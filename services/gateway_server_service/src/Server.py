#!/usr/bin/env python3.10
import asyncio
import sys
import json
import os
import cv2
import time
import traceback
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict

import websockets.asyncio
import websockets.asyncio.server
from websockets.asyncio.server import serve
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
    from common_utilities import ConfigManager
except ImportError:
    ConfigManager = None
from utilities.files_handler import get_client_image
from utilities.Datatypes import Action, Reason
from .ClientChecks import ClientChecks

SERVICES_ROOT_PATH = Path(__file__).resolve().parents[2]
if str(SERVICES_ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(SERVICES_ROOT_PATH))

from RateLimiter_service.src.RateLimiter import RateLimiter
from RateLimiter_service.src.RateLimiterManager import RateLimiterManager


DEFAULT_RATE_LIMIT_MAX_CLIENTS = 100
DEFAULT_RATE_LIMIT_WINDOW_MS = 6000
DEFAULT_IMAGE_CONTENT_TYPE = "image/jpeg"
MESSAGE_WAIT_TIMEOUT_SECONDS = 1000


def _load_config_manager():
    if ConfigManager is not None:
        try:
            return ConfigManager.instance()
        except Exception:
            pass
    max_clients = int(os.getenv("RATE_LIMIT_MAX_CLIENTS", str(DEFAULT_RATE_LIMIT_MAX_CLIENTS)))
    window_ms = int(os.getenv("RATE_LIMIT_WINDOW_MS", str(DEFAULT_RATE_LIMIT_WINDOW_MS)))
    cleanup_ms = int(os.getenv("RATE_LIMIT_CLEANUP_MS", str(window_ms)))
    rate_limiter = SimpleNamespace(
        max_clients=max_clients,
        window_ms=window_ms,
        cleanup_ms=cleanup_ms,
    )
    return SimpleNamespace(rate_limiter=rate_limiter)


class Server(Base_process):
    @staticmethod
    def _initialise_logger(logger: LOGGER | str | None) -> LOGGER:
        if isinstance(logger, str):
            resolved_logger = LOGGER(logger)
            resolved_logger.create_File_logger(logger, log_levels=["DEBUG", "ERROR", "CRITICAL", "WARNING"])
            resolved_logger.create_Stream_logger(log_levels=["INFO", "ERROR", "WARNING"])
            return resolved_logger
        if isinstance(logger, LOGGER):
            return logger
        return LOGGER(None)

    @staticmethod
    def _format_timestamp(epoch_seconds: float) -> str:
        return time.strftime("%H-%M-%S", time.localtime(epoch_seconds))

    def _create_rmq_handler(self) -> Async_RMQ:
        handler = Async_RMQ(logger=self.logs)
        handler.max_retries = 3
        handler.retry_delay = 1
        handler.prefetch_count = 1
        handler.durable_queues = True
        handler.persistent_messages = False
        return handler

    def __init__(
        self,
        process_name,
        serve_ip: str,
        server_port: int,
        endpoint_path: str,
        logger=None,
        config_manager: ConfigManager | None = None,
        rate_limiter_config: Dict[str, int] | None = None,
        storage_client: StorageClient | None = None,
        redis_clients_status: RedisHandler | None = None,
        **kwargs,
    ):
        super().__init__(process_name, None if "process_args" not in kwargs else kwargs["process_args"])
        self.logs = self._initialise_logger(logger)

        self.serve_ip = serve_ip
        self.server_port = server_port
        self.endpoint_path = endpoint_path
        self.config_manager = config_manager or _load_config_manager()
        self.storage_client: StorageClient = storage_client
        if self.storage_client is None:
            raise ValueError("storage_client must be provided for Gateway server")

        self.websocket_max_queue = None

        self.ws: Dict[str, websockets.asyncio.server.ServerConnection] = {}
        self.registered_clients: set[str] = set()
        self.activate_clients: set[str] = set()
        self.clients_join_time: Dict[str, str] = {}
        self.client_checks: ClientChecks = ClientChecks(self.logs)

       
        self.status_store: RedisHandler | None = redis_clients_status or RedisHandler(db=0)
        self._prime_status_store()

     

        self.__rmq_handler = self._create_rmq_handler()

    async def __setup_rmq(self) -> None:
        await self.__rmq_handler.create_producer(
            exchange_name="received_clients_data", exchange_type="direct"
        )
        await self.__rmq_handler.create_consumer()
        await self.__rmq_handler.create_queues("clients_data")
        await self.__rmq_handler.create_queues("actions")
        self.__rmq_connected = True

    def _prime_status_store(self) -> None:
        if not self.status_store:
            return
        try:
            snapshot = self.status_store.get_dict("Clients_status")
        except Exception:
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
            except Exception as exc:
                self.logs.write_logs(
                    f"Unable to initialise Clients_status in Redis: {exc}", LOG_LEVEL.WARNING
                )

    def _read_status_snapshot(self) -> Dict[str, Any]:
        if not self.status_store:
            return {}
        try:
            snapshot = self.status_store.get_dict("Clients_status")
            return snapshot if isinstance(snapshot, dict) else {}
        except Exception as exc:
            self.logs.write_logs(
                f"Failed to read Clients_status from Redis: {exc}", LOG_LEVEL.WARNING
            )
            return {}

    def _update_active_clients_status(self) -> None:
        if not self.status_store:
            return
        try:
            self.status_store.set_dict(
                "Clients_status", {"active_clients": list(self.activate_clients)}
            )
        except Exception as exc:
            self.logs.write_logs(
                f"Failed to update active clients in Redis: {exc}", LOG_LEVEL.WARNING
            )

    def _append_status_entry(self, key: str, value: str) -> None:
        if not self.status_store:
            return
        try:
            snapshot = self._read_status_snapshot()
            bucket = list(snapshot.get(key, []))
            if value not in bucket:
                bucket.append(value)
                self.status_store.set_dict("Clients_status", {key: bucket})
        except Exception as exc:
            self.logs.write_logs(
                f"Failed to append status entry for {key}: {exc}", LOG_LEVEL.WARNING
            )

    async def setup_consumers(self) -> None:
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
                    receive_time_str = self._format_timestamp(receive_time)
                    self.logs.write_logs(
                        f"[TIMING] Client {client_name}: send_time={send_time}, finish_time={finish_time}, receive_time={receive_time_str}",
                        LOG_LEVEL.DEBUG,
                    )
                    if client_name and client_name in self.ws:
                        await self.ws[client_name].send(json.dumps(action2send))
                        sent_time = self._format_timestamp(time.time())
                        self.logs.write_logs(
                            f"Sent response to {client_name} at {sent_time}: {action2send}",
                            LOG_LEVEL.INFO,
                        )
                    else:
                        self.logs.write_logs(
                            f"Client {client_name} not connected or invalid message, state {self.ws.keys()}",
                            LOG_LEVEL.WARNING,
                        )
                        raise RequeueMessage(f"Client {client_name} not connected; requeueing action")
            except ConnectionClosed:
                self.logs.write_logs(
                    f"Connection closed while sending to {client_name}", LOG_LEVEL.WARNING
                )
                self.ws.pop(client_name, None)
                raise RequeueMessage(
                    f"Connection to {client_name} closed mid-send; requeueing action"
                )
            except RequeueMessage as requeue_exc:
                raise requeue_exc
            except Exception as exc:
                error_details = traceback.format_exc()
                self.logs.write_logs(
                    f"Error sending to {client_name}: {exc}\n{error_details}",
                    LOG_LEVEL.ERROR,
                )

    def __register_new_client(
        self, client_name: str, websocket: websockets.asyncio.server.ServerConnection
    ):
        now = datetime.now()
        try:
            client_ip, client_port = websocket.remote_address
        except Exception:
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

    def __cleanup_client(self, client_name: str) -> None:
        if not client_name:
            return
        self.clients_join_time.pop(client_name, None)
        self.activate_clients.discard(client_name)
        self.registered_clients.discard(client_name)
        self.ws.pop(client_name, None)
        self._update_active_clients_status()
        self.logs.write_logs(f"Cleaned up connection for {client_name}", LOG_LEVEL.DEBUG)

    async def handle_connection(self, websocket: websockets.asyncio.server.ServerConnection):
        client_name = ""
        
     
        try:
            while not self.stop_process:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=MESSAGE_WAIT_TIMEOUT_SECONDS)
                except asyncio.TimeoutError:
                    self.logs.write_logs(f"Timeout while awaiting data from {client_name}", LOG_LEVEL.WARNING)
                    await websocket.close()
                    should_cleanup = True
                    break

                now = time.time()
                data: Dict[str, Any] = json.loads(message)
                incoming_client_name = (data.get("user_name") or "").lower().strip()
                if not incoming_client_name:
                    self.logs.write_logs("Received payload without user_name", LOG_LEVEL.WARNING)
                    continue

                if not client_name:
                    client_name = incoming_client_name
                elif incoming_client_name != client_name:
                    self.logs.write_logs(
                        f"Received mismatched user_name '{incoming_client_name}' for active client '{client_name}'",
                        LOG_LEVEL.WARNING,
                    )
                    continue

                status = self._read_status_snapshot()
                paused_clients = set(status.get("paused_clients", []))
                blocked_clients = set(status.get("blocked_clients", []))

                if await self.client_checks.client_is_paused(websocket, client_name, paused_clients):
                    continue
                if await self.client_checks.client_is_blocked(websocket, client_name, blocked_clients):
                    break

                if not await self.client_checks.client_is_available(websocket, client_name, self.activate_clients):
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
                    object_key = await asyncio.to_thread(
                        self.storage_client.store_frame,
                        client_name,
                        frame_bytes,
                        content_type=DEFAULT_IMAGE_CONTENT_TYPE,
                    )
                except Exception as storage_exc:
                    self.logs.write_logs(
                        f"Failed to persist frame for {client_name}: {storage_exc}",
                        LOG_LEVEL.ERROR,
                    )
                    await websocket.close(1011)
                    should_cleanup = True
                    break
                client_payload = {
                    "client_name": client_name,
                    "send_time": self._format_timestamp(now),
                    "frame_size_bytes": len(frame_bytes),
                    "image_object_key": object_key,
                    "image_bucket": self.storage_client.frames_bucket,
                    "image_content_type": DEFAULT_IMAGE_CONTENT_TYPE,
                    "storage_provider": self.storage_client.provider,
                    "user_image": None,
                }

                if client_name not in self.registered_clients:
                    is_registered, client_metadata = self.__register_new_client(client_name, websocket)
                    if not is_registered:
                        break
                    self.registered_clients.add(client_name)
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
            should_cleanup = True
        except ConnectionClosedOK:
            should_cleanup = True
        except Exception as error:
            error_details = traceback.format_exc()
            self.logs.write_logs(
                f"Error from {client_name}: {error}\n{error_details}", LOG_LEVEL.ERROR
            )
            try:
                await websocket.close()
            except Exception:
                pass
            finally:
                should_cleanup = True
        finally:
            if client_name and (should_cleanup or websocket.closed):
                self.__cleanup_client(client_name)

    async def run_server(self):
        rmq_task: asyncio.Task | None = None
        try:
            await self.__setup_rmq()
            await self.setup_consumers()
            rmq_task = asyncio.create_task(self.__rmq_handler.start_consuming())
            self.logs.write_logs("Starting WebSocket server...", LOG_LEVEL.INFO)
            serve_kwargs = {
                "max_size": None,
                "ping_interval": None,
                "ping_timeout": None,
            }
            async with serve(
                self.handle_connection,
                self.serve_ip,
                self.server_port,
                **serve_kwargs,
            ) as websocket_server:
                listen_url = f"ws://{self.serve_ip}:{self.server_port}{self.endpoint_path}"
                self.logs.write_logs(
                    f"Gateway listening on {listen_url}", LOG_LEVEL.INFO
                )
                await websocket_server.serve_forever()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
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
        asyncio.run(self.run_server())
