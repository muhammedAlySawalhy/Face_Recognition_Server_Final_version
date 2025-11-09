#!/usr/bin/env python3.10
from typing import Dict
import asyncio
import time
import traceback
import cv2
import numpy as np
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

    def _delete_frame_if_needed(self, object_key: str | None) -> None:
        if not object_key or not self.storage_client:
            return
        try:
            self.storage_client.delete_object(object_key)
        except Exception as exc:
            self.logs.write_logs(
                f"Failed to delete frame '{object_key}': {exc}", LOG_LEVEL.WARNING
            )

    async def _handle_phone(self, payload, models_manager: ModelsManager):
        object_key = payload.get("image_object_key")
        client_data = None
        try:
            client_data = await asyncio.to_thread(self._hydrate_payload, payload)
            client_data.pop("ref_image", None)
            start_time = time.time()
            result = await asyncio.to_thread(
                models_manager.phone_model_pipeline, client_data
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
            self._delete_frame_if_needed(object_key)

    async def _handle_face(self, payload, models_manager: ModelsManager):
        object_key = payload.get("image_object_key")
        client_data = None
        try:
            client_data = await asyncio.to_thread(self._hydrate_payload, payload)
            client_data.pop("ref_image", None)
            start_time = time.time()
            result = await asyncio.to_thread(
                models_manager.face_model_pipeline, client_data
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
            self._delete_frame_if_needed(object_key)

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

    async def _run_async(self):
        models_manager = self.ModelsInitiation()
        if models_manager is None:
            self.logs.write_logs(
                f"Failed to create models manager for {self.pipeline_name}",
                LOG_LEVEL.CRITICAL,
            )
            return
        await self._init_rmq()
        self._register_consumers(models_manager)
        try:
            await self._rmq.start_consuming()
        finally:
            await self._rmq.close()

    def run(self):
        asyncio.run(self._run_async())

    def ModelsInitiation(self):
        models_manager = None
        try:
            models_manager = ModelsManager(
                **self.model_init_param,
                logger=self.logs,
                storage_client=self.storage_client,
            )
        except Exception:
            track_error = traceback.format_exc()
            self.logs.write_logs(
                f"Error-{self.pipeline_name}:{track_error}", LOG_LEVEL.ERROR
            )
        return models_manager
