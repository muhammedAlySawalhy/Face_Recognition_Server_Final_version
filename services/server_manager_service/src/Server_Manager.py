#!/usr/bin/env python3.10
from typing import Optional
import os
import asyncio
import threading
import time
import traceback
from common_utilities import (
    Base_process,
    LOGGER,
    LOG_LEVEL,
    RedisHandler,
    Async_RMQ,
    StorageClient,
)
from .Save_Action_thread import SaveAction_Thread
from .FastAPIHandler import FastAPIHandler
from .FileOperationsHandler import FileOperationsHandler


class Server_Manager(Base_process):
    def __init__(
        self,
        process_name: str,
        gui_backend_ip: str = "0.0.0.0",
        gui_backend_port: int = 6000,
        logger=None,
        storage_client: Optional[StorageClient] = None,
        **kwargs,
    ):
        super().__init__(process_name)
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
        self.redis_data = kwargs.get("redis_data") or RedisHandler(db=0)
        self.storage_client = storage_client or kwargs.get("storage_client")
        self._rmq = Async_RMQ(logger=self.logs)
        self.gui_backend_ip = gui_backend_ip
        self.gui_backend_port = gui_backend_port
        self.save_action_thread = SaveAction_Thread(
            "SaveAction_Thread", storage_client=self.storage_client
        )
        self.fastapi_handler = FastAPIHandler(
            thread_name="FastAPIHandler_Thread",
            gui_backend_ip=gui_backend_ip,
            gui_backend_port=gui_backend_port,
            redis_data=self.redis_data,
            logger=self.logs,
        )
        self.file_ops_handler = FileOperationsHandler(
            thread_name="FileOperationsHandler_Thread",
            redis_data=self.redis_data,
            logger=self.logs,
        )
        self._consumer_thread: Optional[threading.Thread] = None

    def _handle_saved_action(self, payload: dict):
        try:
            user_name = payload.get("user_name")
            action_reason = payload.get("Action_Reason")
            action_image = payload.get("Action_image")
            action_object_key = payload.get("action_image_object_key")
            action_bucket = payload.get("action_image_bucket")
            if user_name and action_reason:
                self.save_action_thread.add_to_queue(
                    user_name,
                    action_reason,
                    action_image,
                    action_object_key,
                    action_bucket,
                )
        except Exception as exc:
            track_error = traceback.format_exc()
            self.logs.write_logs(
                f"Failed to handle saved action payload: {exc}\n{track_error}",
                LOG_LEVEL.ERROR,
            )

    async def _run_saved_actions_consumer(self):
        retries = int(os.getenv("RMQ_SETUP_RETRIES", "10"))
        delay = float(os.getenv("RMQ_SETUP_DELAY_SECONDS", "3"))
        for attempt in range(1, retries + 1):
            try:
                await self._rmq.create_producer()
                await self._rmq.create_consumer()
                await self._rmq.create_queues("saved_actions")
                break
            except Exception as exc:
                level = LOG_LEVEL.WARNING if attempt < retries else LOG_LEVEL.ERROR
                self.logs.write_logs(
                    f"Error setting up RMQ for saved_actions (attempt {attempt}/{retries}): {exc}",
                    level,
                )
                if attempt >= retries:
                    raise
                await asyncio.sleep(delay)

        @self._rmq.consume_messages(queue_name="saved_actions")
        async def saved_handler(payload):
            await asyncio.to_thread(self._handle_saved_action, payload)

        await self._rmq.start_consuming()

    def _start_rmq_thread(self):
        def runner():
            asyncio.run(self._run_saved_actions_consumer())

        self._consumer_thread = threading.Thread(
            target=runner, name="saved_actions_consumer", daemon=True
        )
        self._consumer_thread.start()

    def _restart_fastapi_handler(self):
        self.fastapi_handler.Stop_thread()
        self.fastapi_handler.Join_thread()
        self.fastapi_handler = FastAPIHandler(
            thread_name="FastAPIHandler_Thread",
            gui_backend_ip=self.gui_backend_ip,
            gui_backend_port=self.gui_backend_port,
            redis_data=self.redis_data,
            logger=self.logs,
        )
        self.fastapi_handler.Start_thread()

    def _restart_file_ops_handler(self):
        self.file_ops_handler.Stop_thread()
        self.file_ops_handler.Join_thread()
        self.file_ops_handler = FileOperationsHandler(
            thread_name="FileOperationsHandler_Thread",
            redis_data=self.redis_data,
            logger=self.logs,
        )
        self.file_ops_handler.Start_thread()

    def _start_worker_threads(self):
        if not self.save_action_thread.is_started():
            self.save_action_thread.Start_thread()
        if not self.fastapi_handler.is_started():
            self.fastapi_handler.Start_thread()
        if not self.file_ops_handler.is_started():
            self.file_ops_handler.Start_thread()

    def _monitor_threads(self):
        if not self.fastapi_handler.is_started():
            self.logs.write_logs(
                "FastAPI handler thread died, restarting...",
                LOG_LEVEL.WARNING,
            )
            self._restart_fastapi_handler()
        if not self.file_ops_handler.is_started():
            self.logs.write_logs(
                "File operations handler thread died, restarting...",
                LOG_LEVEL.WARNING,
            )
            self._restart_file_ops_handler()
        if self._consumer_thread and not self._consumer_thread.is_alive():
            self.logs.write_logs(
                "Saved actions consumer stopped, restarting...",
                LOG_LEVEL.WARNING,
            )
            self._start_rmq_thread()

    def run(self):
        try:
            self._start_worker_threads()
            self._start_rmq_thread()
            while not self.stop_process:
                time.sleep(1)
                self._monitor_threads()
        except KeyboardInterrupt:
            pass
        except Exception:
            track_error = traceback.format_exc()
            self.logs.write_logs(
                f"Error-{self.process_name}:{track_error}",
                LOG_LEVEL.ERROR,
            )
        finally:
            try:
                self.fastapi_handler.Stop_thread()
                self.fastapi_handler.Join_thread()
            except Exception as exc:
                self.logs.write_logs(
                    f"Error stopping FastAPI handler: {exc}",
                    LOG_LEVEL.ERROR,
                )
            try:
                self.file_ops_handler.Stop_thread()
                self.file_ops_handler.Join_thread()
            except Exception as exc:
                self.logs.write_logs(
                    f"Error stopping File operations handler: {exc}",
                    LOG_LEVEL.ERROR,
                )
            try:
                self.save_action_thread.Stop_thread()
                self.save_action_thread.Join_thread()
            except Exception as exc:
                self.logs.write_logs(
                    f"Error stopping SaveAction thread: {exc}",
                    LOG_LEVEL.ERROR,
                )
            try:
                asyncio.run(self._rmq.close())
            except Exception as exc:
                self.logs.write_logs(
                    f"Error closing RMQ connections: {exc}",
                    LOG_LEVEL.ERROR,
                )
