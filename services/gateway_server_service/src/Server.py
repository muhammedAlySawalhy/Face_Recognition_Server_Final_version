#!/usr/bin/env python3.10
import asyncio
from pathlib import Path
import sys
import json
import os
import cv2
import numpy as np
import time
import traceback
from datetime import datetime
from typing import Any, Dict

import websockets.asyncio
from websockets.asyncio.server import serve
import websockets.asyncio.server
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK

from common_utilities import (
    Base_process,
    LOGGER,
    LOG_LEVEL,
    RedisHandler,
    encoded64image2cv2,
    Async_RMQ,
    RequeueMessage,
    StorageClient,
)

try:
    from common_utilities import ConfigManager  # type: ignore
except ImportError:  # pragma: no cover
    ConfigManager = None  # type: ignore
from utilities.files_handler import get_client_image
from utilities.Datatypes import Action, Reason
from .ClientChecks import ClientChecks

SERVICES_ROOT_PATH = Path(__file__).resolve().parents[2]
if str(SERVICES_ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(SERVICES_ROOT_PATH))

from RateLimiter_service.src.RateLimiter import RateLimiter  # pylint: disable=wrong-import-position
from RateLimiter_service.src.RateLimiterManager import RateLimiterManager  # pylint: disable=wrong-import-position


def _load_config_manager():
    if ConfigManager is not None:
        try:
            return ConfigManager.instance()
        except Exception:  # pragma: no cover
            pass
    max_clients = int(os.getenv("RATE_LIMIT_MAX_CLIENTS", "100"))
    window_ms = int(os.getenv("RATE_LIMIT_WINDOW_MS", "6000"))
    cleanup_ms = int(os.getenv("RATE_LIMIT_CLEANUP_MS", str(window_ms)))

    class _RateLimiterFallback:
        max_clients = max_clients
        window_ms = window_ms
        cleanup_ms = cleanup_ms

    class _ConfigFallback:
        rate_limiter = _RateLimiterFallback()

    return _ConfigFallback()


class Server(Base_process):
    def __init__(
        self,
        process_name,
        serve_ip: str,
        server_port: int,
        endpoint_path: str,
        logger=None,
        config_manager: ConfigManager | None = None,
        rate_limiter_config: Dict[str, int] | None = None,
        websocket_limits: Dict[str, int] | None = None,
        storage_client: StorageClient | None = None,
        redis_clients_status: RedisHandler | None = None,
        **kwargs,
    ):
        super().__init__(process_name, None if "process_args" not in kwargs else kwargs["process_args"])
        if isinstance(logger, str):
            self.logs = LOGGER(logger)
            self.logs.create_File_logger(
                f"{logger}", log_levels=["DEBUG", "ERROR", "CRITICAL", "WARNING"]
            )
            self.logs.create_Stream_logger(log_levels=["INFO", "ERROR", "WARNING"])
        elif isinstance(logger, LOGGER):
            self.logs = logger
        else:
            self.logs = LOGGER(None)

        self.serve_ip = serve_ip
        self.server_port = server_port
        self.endpoint_path = endpoint_path
        self.config_manager = config_manager or _load_config_manager()
        self.storage_client: StorageClient = storage_client
        if self.storage_client is None:
            raise ValueError("storage_client must be provided for Gateway server")

        limits = websocket_limits or {}
        semaphore_size = max(1, int(limits.get("semaphore", self.config_manager.rate_limiter.max_clients)))
        self.connection_semaphore = asyncio.Semaphore(semaphore_size)
        self.websocket_max_queue = int(
            limits.get("max_queue", self.config_manager.rate_limiter.max_clients * 6)
        )

        self.ws: Dict[str, websockets.asyncio.server.ServerConnection] = {}
        self.registered_clients: list[str] = []
        self.activate_clients: set[str] = set()
        self.clients_join_time: Dict[str, str] = {}
        self.client_checks: ClientChecks = ClientChecks(self.logs)

        self.status_store: RedisHandler | None = redis_clients_status or RedisHandler(db=0)
        self._prime_status_store()

        limiter_cfg = rate_limiter_config or {
            "max_clients": self.config_manager.rate_limiter.max_clients,
            "window_size_in_millis": self.config_manager.rate_limiter.window_ms,
            "cleanup_interval_in_millis": self.config_manager.rate_limiter.cleanup_ms,
        }
        self._rate_limiter_manager: RateLimiterManager | None = None
        try:
            self._rate_limiter_manager = RateLimiterManager.get_instance(RateLimiter, limiter_cfg)
            self.logs.write_logs(
                "Rate limiter initialised -> max %s clients every %s ms"
                % (limiter_cfg["max_clients"], limiter_cfg["window_size_in_millis"]),
                LOG_LEVEL.INFO,
            )
        except Exception as rate_limiter_error:  # pylint: disable=broad-except
            self.logs.write_logs(
                f"Failed to initialise rate limiter: {rate_limiter_error}", LOG_LEVEL.ERROR
            )

        self.__rmq_handler = Async_RMQ(logger=self.logs)
        self.__rmq_connected = False
        self.__rmq_handler.max_retries = 3
        self.__rmq_handler.retry_delay = 1
        self.__rmq_handler.prefetch_count = 1
        self.__rmq_handler.durable_queues = True
        self.__rmq_handler.persistent_messages = False

    # ------------------------------------------------------------------------------------------------------------------#
    async def __setup_rmq(self) -> None:
        await self.__rmq_handler.create_producer(
            exchange_name="received_clients_data", exchange_type="direct"
        )
        await self.__rmq_handler.create_consumer()
        await self.__rmq_handler.create_queues("clients_data")
        await self.__rmq_handler.create_queues("actions")
        self.__rmq_connected = True

    # ------------------------------------------------------------------------------------------------------------------#
    def _prime_status_store(self) -> None:
        if not self.status_store:
            return
        try:
            snapshot = self.status_store.get_dict("Clients_status")
        except Exception:  # pylint: disable=broad-except
            snapshot = None
        if not snapshot:
            base_payload = {
                "active_clients": [],
                "deactivate_clients": [],
                "blocked_clients": [],
                "paused_clients": [],
                "connecting_internet_error": [],
                "clients_to_close": [],
            }
            try:
                self.status_store.set_dict("Clients_status", base_payload)
            except Exception as exc:  # pylint: disable=broad-except
                self.logs.write_logs(
                    f"Unable to initialise Clients_status in Redis: {exc}", LOG_LEVEL.WARNING
                )

    # ------------------------------------------------------------------------------------------------------------------#
    def _read_status_snapshot(self) -> Dict[str, Any]:
        if not self.status_store:
            return {}
        try:
            snapshot = self.status_store.get_dict("Clients_status")
            return snapshot if isinstance(snapshot, dict) else {}
        except Exception as exc:  # pylint: disable=broad-except
            self.logs.write_logs(
                f"Failed to read Clients_status from Redis: {exc}", LOG_LEVEL.WARNING
            )
            return {}

    # ------------------------------------------------------------------------------------------------------------------#
    def _update_active_clients_status(self) -> None:
        if not self.status_store:
            return
        try:
            self.status_store.set_dict(
                "Clients_status", {"active_clients": sorted(self.activate_clients)}
            )
        except Exception as exc:  # pylint: disable=broad-except
            self.logs.write_logs(
                f"Failed to update active clients in Redis: {exc}", LOG_LEVEL.WARNING
            )

    # ------------------------------------------------------------------------------------------------------------------#
    def _append_status_entry(self, key: str, value: str) -> None:
        if not self.status_store:
            return
        try:
            snapshot = self._read_status_snapshot()
            bucket = list(snapshot.get(key, []))
            if value not in bucket:
                bucket.append(value)
                self.status_store.set_dict("Clients_status", {key: bucket})
        except Exception as exc:  # pylint: disable=broad-except
            self.logs.write_logs(
                f"Failed to append status entry for {key}: {exc}", LOG_LEVEL.WARNING
            )

    # ////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    async def setup_consumers(self) -> None:
        """Setup RMQ consumers with proper error handling."""

        @self.__rmq_handler.consume_messages(queue_name="actions")
        async def send_action(action):
            client_name = None
            receive_time = time.time()
            try:
                if action and isinstance(action, dict):
                    action2send = action
                    client_name = action2send.get("client_name")
                    send_time = action2send.get("send_time", "unknown")
                    finish_time = action2send.get("finish_time", "unknown")
                    receive_time_str = time.strftime(
                        "%H-%M-%S", time.localtime(receive_time)
                    )
                    self.logs.write_logs(
                        f"[TIMING] Client {client_name}: send_time={send_time}, finish_time={finish_time}, receive_time={receive_time_str}",
                        LOG_LEVEL.DEBUG,
                    )
                    if client_name and client_name in self.ws:
                        await self.ws[client_name].send(json.dumps(action2send))
                        sent_time = time.strftime("%H-%M-%S", time.localtime())
                        self.logs.write_logs(
                            f"Sent response to {client_name} at {sent_time}: {action2send}",
                            LOG_LEVEL.INFO,
                        )
                    else:
                        self.logs.write_logs(
                            f"Client {client_name} not connected or invalid message",
                            LOG_LEVEL.WARNING,
                        )
                        raise RequeueMessage(f"Client {client_name} not connected; requeueing action")
            except ConnectionClosed:
                self.logs.write_logs(
                    f"Connection closed while sending to {client_name}", LOG_LEVEL.WARNING
                )
            except RequeueMessage as requeue_exc:
                # Allow Async_RMQ to requeue the message by re-raising
                raise requeue_exc
            except Exception as exc:  # pylint: disable=broad-except
                error_details = traceback.format_exc()
                self.logs.write_logs(
                    f"Error sending to {client_name}: {exc}\n{error_details}",
                    LOG_LEVEL.ERROR,
                )

    # ////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __register_new_client(
        self, client_name: str, websocket: websockets.asyncio.server.ServerConnection
    ):
        now = datetime.now()
        try:
            client_ip, client_port = websocket.remote_address
        except Exception:  # pylint: disable=broad-except
            client_ip, client_port = ("unknown", 0)
        client_metadata = {
            "client_name": client_name,
            "client_ip": client_ip,
            "client_port": client_port,
        }
        join_time_str = now.isoformat(timespec="milliseconds")
        self.clients_join_time[client_name] = join_time_str
        if client_name not in self.activate_clients:
            self.activate_clients.add(client_name)
        self._update_active_clients_status()

        ref_image = get_client_image(client_name)
        if ref_image is None:
            self.logs.write_logs(f"No reference image for {client_name}", LOG_LEVEL.WARNING)
            return False, None
        self.ws[client_name] = websocket
        return True, client_metadata

    # ------------------------------------------------------------------------------------------------------------------#
    def __cleanup_client(self, client_name: str) -> None:
        if not client_name:
            return
        self.clients_join_time.pop(client_name, None)
        self.activate_clients.discard(client_name)
        if client_name in self.registered_clients:
            self.registered_clients.remove(client_name)
        self.ws.pop(client_name, None)
        self._update_active_clients_status()
        self.logs.write_logs(f"Cleaned up connection for {client_name}", LOG_LEVEL.DEBUG)

    # ////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    async def handle_connection(self, websocket: websockets.asyncio.server.ServerConnection):
        client_name = ""
        await self.connection_semaphore.acquire()
        try:
            while not self.stop_process:
                status = self._read_status_snapshot()
                paused_clients = status.get("paused_clients", [])
                blocked_clients = status.get("blocked_clients", [])

                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1000)
                except asyncio.TimeoutError:
                    self.logs.write_logs(f"Timeout while awaiting data from {client_name}", LOG_LEVEL.WARNING)
                    await websocket.close()
                    break

                now = time.time()
                data: Dict[str, Any] = json.loads(message)
                client_name = (data.get("user_name") or "").lower().strip()
                if not client_name:
                    self.logs.write_logs("Received payload without user_name", LOG_LEVEL.WARNING)
                    continue

                if await self.client_checks.client_is_paused(websocket, client_name, paused_clients):
                    continue
                if await self.client_checks.client_is_blocked(websocket, client_name, blocked_clients):
                    break

                if not await self.client_checks.client_is_available(websocket, client_name, self.activate_clients):
                    break

                if self._rate_limiter_manager and not self._rate_limiter_manager.allow_request(client_name):
                    await websocket.send(
                        json.dumps(
                            {
                                "action": Action.ACTION_ERROR.value,
                                "reason": Reason.REASON_RATE_LIMIT_EXCEEDED.value,
                            }
                        )
                    )
                    await websocket.close(4003)
                    self.logs.write_logs(
                        f"Rate limit exceeded for client {client_name}", LOG_LEVEL.WARNING
                    )
                    break

                self.logs.write_logs(f"user {client_name} sent data !!", LOG_LEVEL.INFO)
                user_image = encoded64image2cv2(data.get("image"))
                if user_image is None:
                    self.logs.write_logs(f"No image from {client_name}", LOG_LEVEL.WARNING)
                    continue

                encoded_ok, buffer = cv2.imencode(".jpg", user_image)
                if not encoded_ok:
                    self.logs.write_logs(
                        f"Failed to encode frame for {client_name}", LOG_LEVEL.ERROR
                    )
                    continue
                frame_bytes = buffer.tobytes()
                try:
                    object_key = self.storage_client.store_frame(
                        client_name, frame_bytes, content_type="image/jpeg"
                    )
                except Exception as storage_exc:  # pylint: disable=broad-except
                    self.logs.write_logs(
                        f"Failed to persist frame for {client_name}: {storage_exc}",
                        LOG_LEVEL.ERROR,
                    )
                    await websocket.close(1011)
                    break
                client_payload = {
                    "client_name": client_name,
                    "send_time": time.strftime("%H-%M-%S", time.localtime(now)),
                    "frame_size_bytes": len(frame_bytes),
                }
                if self.storage_client:
                    client_payload.update(
                        image_object_key=object_key,
                        image_bucket=self.storage_client.frames_bucket,
                        image_content_type="image/jpeg",
                        storage_provider=self.storage_client.provider,
                        user_image=None,
                    )

                if client_name not in self.registered_clients:
                    is_registered, client_metadata = self.__register_new_client(client_name, websocket)
                    if not is_registered:
                        break
                    self.registered_clients.append(client_name)
                    client_payload.update(client_metadata)

                published = await self.__rmq_handler.publish_data(client_payload, "clients_data")
                if not published:
                    self.logs.write_logs(
                        f"Failed to publish data for {client_name}", LOG_LEVEL.ERROR
                    )

        except ConnectionClosed as closed:
            self.logs.write_logs(f"Connection closed for {client_name}, code {closed.code}", LOG_LEVEL.WARNING)
            if closed.code == 4000:
                self._append_status_entry("connecting_internet_error", client_name)
        except ConnectionClosedOK:
            pass
        except Exception as error:  # pylint: disable=broad-except
            error_details = traceback.format_exc()
            self.logs.write_logs(
                f"Error from {client_name}: {error}\n{error_details}", LOG_LEVEL.ERROR
            )
            try:
                await websocket.close()
            except Exception:  # pylint: disable=broad-except
                pass
        finally:
            self.__cleanup_client(client_name)
            self.connection_semaphore.release()

    # ------------------------------------------------------------------------------------------------------------------#
    async def run_server(self):
        """Run the server with proper RMQ connection management."""
        rmq_task: asyncio.Task | None = None
        try:
            await self.__setup_rmq()
            await self.setup_consumers()
            rmq_task = asyncio.create_task(self.__rmq_handler.start_consuming())
            self.logs.write_logs("Starting WebSocket server...", LOG_LEVEL.INFO)
            async with serve(
                self.handle_connection,
                self.serve_ip,
                self.server_port,
                max_size=None,
                max_queue=self.websocket_max_queue,
                ping_interval=None,
                ping_timeout=None,
            ) as websocket_server:
                listen_url = f"ws://{self.serve_ip}:{self.server_port}{self.endpoint_path}"
                self.logs.write_logs(
                    f"Gateway listening on {listen_url}", LOG_LEVEL.INFO
                )
                await websocket_server.serve_forever()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pylint: disable=broad-except
            self.logs.write_logs(f"Gateway server crashed: {exc}", LOG_LEVEL.CRITICAL)
            self.logs.write_logs(traceback.format_exc(), LOG_LEVEL.DEBUG)
            raise
        finally:
            if rmq_task:
                rmq_task.cancel()
                try:
                    await rmq_task
                except asyncio.CancelledError:
                    pass
            await self.__rmq_handler.close()

    def run(self):
        """Entry point for Base_process."""
        asyncio.run(self.run_server())
