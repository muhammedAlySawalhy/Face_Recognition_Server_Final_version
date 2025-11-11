#!/usr/bin/env python3.10
from typing import Dict
import asyncio
import time
import traceback
import cv2
import numpy as np
import functools
from concurrent.futures import ThreadPoolExecutor
from common_utilities import LOGGER, LOG_LEVEL, Base_process, Async_RMQ
from .ModelsManager import ModelsManager


class PipeLine(Base_process):
    def __init__(
        self,
        pipeline_name,
        models_init_parameters: Dict[str, str],
        logger=None,
        storage_client=None,
    ):
        super().__init__(process_name=pipeline_name)
        if isinstance(logger, str):
            self.logs = LOGGER(logger)
            self.logs.create_File_logger(
                f"{logger}",
                log_levels=["DEBUG", "INFO", "ERROR", "CRITICAL", "WARNING"],
            )
            self.logs.create_Stream_logger(log_levels=["INFO", "ERROR", "WARNING"])
        elif isinstance(logger, LOGGER):
            self.logs = logger
        else:
            self.logs = LOGGER(None)
        self.pipeline_name = pipeline_name
        self.model_init_param = models_init_parameters
        self.storage_client = storage_client
        self._rmq = Async_RMQ(logger=self.logs)
        self._phone_executor: ThreadPoolExecutor | None = None
        self._face_executor: ThreadPoolExecutor | None = None

    def _hydrate_payload(self, payload: dict) -> dict:
        client_data = dict(payload)
        if (
            self.storage_client
            and client_data.get("user_image") is None
            and client_data.get("image_object_key")
        ):
            object_key = client_data["image_object_key"]
            try:
                frame_bytes = self.storage_client.fetch_object(object_key)
                array = np.frombuffer(frame_bytes, dtype=np.uint8)
                image = cv2.imdecode(array, cv2.IMREAD_COLOR)
                client_data["user_image"] = image
            except Exception as exc:
                self.logs.write_logs(
                    f"Failed to hydrate frame '{object_key}': {exc}",
                    LOG_LEVEL.ERROR,
                )
                client_data["user_image"] = None
        return client_data

    

    async def _handle_phone(self, payload, models_manager: ModelsManager):
        object_key = payload.get("image_object_key")
        client_data = None
        try:
            client_data = await self._run_in_executor(
                self._phone_executor, self._hydrate_payload, payload
            )
            client_data.pop("ref_image", None)
            start_time = time.time()
            result = await self._run_in_executor(
                self._phone_executor, models_manager.phone_model_pipeline, client_data
            )
            publish_payload = {**result, **client_data}
            publish_payload.pop("user_image", None)
            await self._rmq.publish_data(publish_payload, "phone_pipeline_results")
            self.logs.write_logs(
                f"Execution time for Phone pipeline is {time.time() - start_time} for {client_data['client_name']}",
                LOG_LEVEL.DEBUG,
            )
        except Exception as exc:
            track_error = traceback.format_exc()
            self.logs.write_logs(
                f"Error in phone pipeline: {exc}\n{track_error}",
                LOG_LEVEL.ERROR,
            )
            failure_payload = dict(payload)
            failure_payload.update(
                {
                    "pipeline": "phone",
                    "processing_error": str(exc),
                    "processing_traceback": track_error,
                }
            )
            failure_payload.pop("user_image", None)
            await self._rmq.publish_data(failure_payload, "phone_pipeline_results")
        finally:
            if client_data:
                client_data.pop("user_image", None)
          

    async def _handle_face(self, payload, models_manager: ModelsManager):
        object_key = payload.get("image_object_key")
        client_data = None
        try:
            client_data = await self._run_in_executor(
                self._face_executor, self._hydrate_payload, payload
            )
            client_data.pop("ref_image", None)
            start_time = time.time()
            result = await self._run_in_executor(
                self._face_executor, models_manager.face_model_pipeline, client_data
            )
            publish_payload = {**result, **client_data}
            publish_payload.pop("user_image", None)
            await self._rmq.publish_data(publish_payload, "face_pipeline_results")
            self.logs.write_logs(
                f"Execution time for Face pipeline is {time.time() - start_time} for {client_data['client_name']}",
                LOG_LEVEL.DEBUG,
            )
        except Exception as exc:
            track_error = traceback.format_exc()
            self.logs.write_logs(
                f"Error in face pipeline: {exc}\n{track_error}",
                LOG_LEVEL.ERROR,
            )
            failure_payload = dict(payload)
            failure_payload.update(
                {
                    "pipeline": "face",
                    "processing_error": str(exc),
                    "processing_traceback": track_error,
                }
            )
            failure_payload.pop("user_image", None)
            await self._rmq.publish_data(failure_payload, "face_pipeline_results")
        finally:
            if client_data:
                client_data.pop("user_image", None)
          

    def _register_consumers(self, models_manager: ModelsManager):
        @self._rmq.consume_messages(
            queue_name=f"{self.pipeline_name}_phone_data"
        )
        async def phone_handler(payload):
            await self._handle_phone(payload, models_manager)

        @self._rmq.consume_messages(
            queue_name=f"{self.pipeline_name}_face_data"
        )
        async def face_handler(payload):
            await self._handle_face(payload, models_manager)

    async def _init_rmq(self):
        queue_args = None
        await self._rmq.create_producer(
            exchange_name="pipeline_results", exchange_type="direct"
        )
        await self._rmq.create_consumer(
            exchange_name="received_clients_data", exchange_type="direct"
        )
        await self._rmq.create_queues(
            "face_pipeline_results",
            routing_key="face_results",
            exchange_name="pipeline_results",
        )
        await self._rmq.create_queues(
            "phone_pipeline_results",
            routing_key="phone_results",
            exchange_name="pipeline_results",
        )
        await self._rmq.create_queues(
            [f"{self.pipeline_name}_face_data", f"{self.pipeline_name}_phone_data"],
            routing_key=self.pipeline_name,
            exchange_name="received_clients_data",
            queue_arguments=queue_args,
        )

    def _initialise_executors(self):
        if self._phone_executor is None:
            self._phone_executor = ThreadPoolExecutor(
                max_workers=1, thread_name_prefix=f"{self.pipeline_name}-phone"
            )
        if self._face_executor is None:
            self._face_executor = ThreadPoolExecutor(
                max_workers=1, thread_name_prefix=f"{self.pipeline_name}-face"
            )

    def _shutdown_executors(self):
        for executor in (self._phone_executor, self._face_executor):
            if executor is not None:
                executor.shutdown(wait=True)
        self._phone_executor = None
        self._face_executor = None

    async def _run_in_executor(self, executor, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            executor, functools.partial(func, *args, **kwargs)
        )

    async def _run_async(self):
        self._initialise_executors()
        models_manager = self.ModelsInitiation()
        if models_manager is None:
            self.logs.write_logs(
                f"Failed to create models manager for {self.pipeline_name}",
                LOG_LEVEL.CRITICAL,
            )
            self._shutdown_executors()
            return
        await self._init_rmq()
        self._register_consumers(models_manager)
        try:
            await self._rmq.start_consuming()
        finally:
            await self._rmq.close()
            self._shutdown_executors()

    def run(self):
        asyncio.run(self._run_async())

    def ModelsInitiation(self):
        models_manager = None
        try:
            models_manager = ModelsManager(**self.model_init_param, logger=self.logs)
        except Exception:
            track_error = traceback.format_exc()
            self.logs.write_logs(
                f"Error-{self.pipeline_name}:{track_error}", LOG_LEVEL.ERROR
            )
        return models_manager
