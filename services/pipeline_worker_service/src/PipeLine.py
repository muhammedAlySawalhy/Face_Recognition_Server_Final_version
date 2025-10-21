#!/usr/bin/env python3.10
from .ModelsManager import ModelsManager
from typing import Dict
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np

from common_utilities import LOGGER, LOG_LEVEL, Base_process, Sync_RMQ
import torch.multiprocessing as mp
import threading
import traceback
import time


class PipeLine(Base_process):
    def __init__(
        self,
        pipeline_name,
        models_init_parameters: Dict[str, str],
        Max_clients=10,
        logger=None,
        storage_client=None,
    ):
        # _________________________________________________________________________#
        super().__init__(process_name=pipeline_name)
        # _________________________________________________________________________#
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
        # _________________________________________________________________________#
        self.pipeline_name = pipeline_name
        self.MAX_CLIENTS = Max_clients
        self.model_init_param = models_init_parameters
        self.storage_client = storage_client
        self.data_manager = mp.Manager()
        self.pipeline_clients = self.data_manager.list()
        self.pipeline_clients_count = 0
        self.__STOP = self.data_manager.Value("b", False)
        self.lock_Data = threading.Lock()
        self.__rmq_handler = Sync_RMQ(logger=self.logs)
        # Configure RMQ for better memory management
        self.__rmq_handler.max_retries = 3
        self.__rmq_handler.retry_delay = 1
        self.__rmq_handler.prefetch_count = 1  # Limit concurrent processing
        self.__rmq_handler.durable_queues = True  # Ensure queue durability
        self.__rmq_handler.persistent_messages = (
            False  # Don't persist messages to reduce disk usage
        )
        self._executor = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix=f"{self.pipeline_name}_worker"
        )
        self._cleanup_lock = threading.Lock()
        self._deleted_storage_keys = set()

    # //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __del__(self):
        if hasattr(self, "pipeline_clients"):
            del self.pipeline_clients
        self.data_manager.shutdown()
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=True)

    # //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def assigned_clients(self, client_name) -> bool:
        if self.pipeline_clients_count < self.MAX_CLIENTS:
            with self.lock_Data:
                self.pipeline_clients_count += 1
                self.pipeline_clients.append(client_name)
            return True
        else:
            return False

    def unassigned_clients(self, client_name) -> bool:
        if client_name in self.pipeline_clients:
            with self.lock_Data:
                self.pipeline_clients_count -= 1
                self.pipeline_clients.remove(client_name)
            return True
        else:
            return False

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
            except Exception as exc:  # pylint: disable=broad-except
                self.logs.write_logs(
                    f"Failed to hydrate frame '{object_key}': {exc}", LOG_LEVEL.ERROR
                )
                client_data["user_image"] = None
        return client_data

    def _mark_storage_key_for_cleanup(self, object_key: str) -> bool:
        with self._cleanup_lock:
            if object_key in self._deleted_storage_keys:
                return False
            # Prevent unbounded growth – clear occasionally
            if len(self._deleted_storage_keys) > 50000:
                self._deleted_storage_keys.clear()
            self._deleted_storage_keys.add(object_key)
            return True

    def _cleanup_storage(self, client_data: dict) -> None:
        if not self.storage_client:
            return
        object_key = client_data.get("image_object_key")
        if not object_key:
            return
        if not self._mark_storage_key_for_cleanup(object_key):
            return
        try:
            self.storage_client.delete_object(object_key)
            self.logs.write_logs(
                f"Deleted processed frame '{object_key}' from storage",
                LOG_LEVEL.DEBUG,
            )
        except Exception as exc:  # pylint: disable=broad-except
            self.logs.write_logs(
                f"Failed to delete frame '{object_key}' from storage: {exc}",
                LOG_LEVEL.WARNING,
            )
            with self._cleanup_lock:
                self._deleted_storage_keys.discard(object_key)

    # //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def setup_consumers(self, models_manager: ModelsManager):
        """Setup RMQ consumers with models_manager"""

        @self.__rmq_handler.consume_messages(
            queue_name=f"{self.pipeline_name}_phone_data", executor=self._executor
        )
        def phone_detection_pipeline(payload):
            try:
                client_data = self._hydrate_payload(payload)
                client_data.pop("ref_image", None)
                start_time = time.time()
                phone_detection_result = models_manager.phone_model_pipeline(
                    client_data
                )
                publish_payload = {**phone_detection_result, **client_data}
                publish_payload.pop("user_image", None)

                # Publish to separate phone_pipeline_results queue
                self.__rmq_handler.publish_data(
                    publish_payload, "phone_pipeline_results"
                )

                self.logs.write_logs(
                    f"Execution time for Phone pipeline is {time.time() - start_time} for {client_data['client_name']}",
                    logs_level=LOG_LEVEL.DEBUG,
                )
            except Exception as exc:
                track_error = traceback.format_exc()
                self.logs.write_logs(
                    f"Error in phone_detection_pipeline: {exc}\n{track_error}",
                    LOG_LEVEL.ERROR,
                )

        @self.__rmq_handler.consume_messages(
            queue_name=f"{self.pipeline_name}_face_data", executor=self._executor
        )
        def recognition_anti_spoof_pipeline(payload):
            client_data = None
            try:
                client_data = self._hydrate_payload(payload)
                client_data.pop("ref_image", None)
                start_time = time.time()
                recognition_anti_spoof_result = models_manager.face_model_pipeline(
                    client_data
                )
                publish_payload = {**recognition_anti_spoof_result, **client_data}
                publish_payload.pop("user_image", None)

                # Publish to separate face_pipeline_results queue
                self.__rmq_handler.publish_data(
                    publish_payload, "face_pipeline_results"
                )

                self.logs.write_logs(
                    f"Execution time for Face pipeline is {time.time() - start_time} for {client_data['client_name']}",
                    logs_level=LOG_LEVEL.DEBUG,
                )
            except Exception as exc:
                track_error = traceback.format_exc()
                self.logs.write_logs(
                    f"Error in recognition_anti_spoof_pipeline: {exc}\n{track_error}",
                    LOG_LEVEL.ERROR,
                )
                self.__STOP.value = True
            finally:
                # Leave frame objects in storage; downstream consumers (Decision Manager,
                # audit tooling) still need them. Bucket lifecycle handles eventual cleanup.
                pass

    # //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __setup_RMQ_connections(self):
        """Setup RMQ connections and queues"""
        # Create queues with TTL (400ms = 400 milliseconds)
        queue_args = {
            "x-message-ttl": 400,  # Messages expire after 400ms
            "x-max-length": self.MAX_CLIENTS,  # Maximum  messages in queue
            "x-overflow": "drop-head",  # Drop oldest messages when queue is full
        }
        try:
            self.__rmq_handler.create_producer(
                exchange_name="pipeline_results", exchange_type="direct"
            )
            self.__rmq_handler.create_consumer(
                exchange_name="received_clients_data", exchange_type="direct"
            )
            self.__rmq_handler.create_queues(
                "face_pipeline_results",
                routing_key="face_results",
                exchange_name="pipeline_results",
            )  # For face pipeline results
            self.__rmq_handler.create_queues(
                "phone_pipeline_results",
                routing_key="phone_results",
                exchange_name="pipeline_results",
            )  # For phone pipeline results
            self.__rmq_handler.create_queues(
                [f"{self.pipeline_name}_face_data", f"{self.pipeline_name}_phone_data"],
                routing_key=self.pipeline_name,
                exchange_name="received_clients_data",
                queue_arguments=queue_args,
            )
            self.logs.write_logs(
                f">>>*  {self.pipeline_name}: RMQ connections setup completed",
                LOG_LEVEL.DEBUG,
            )
        except Exception as e:
            self.logs.write_logs(
                f"Error setting up RMQ connections: {e}", LOG_LEVEL.ERROR
            )
            raise

    # //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def run(self):
        models_manager = self.ModelsInitiation()
        self.logs.write_logs(
            f">>>*  {self.pipeline_name}: Successfully Create Models Manger",
            LOG_LEVEL.DEBUG,
        )

        # Setup RMQ connections
        self.__setup_RMQ_connections()
        # Setup consumers with models_manager
        self.setup_consumers(models_manager)

        try:
            self.logs.write_logs(
                f">>>*  {self.pipeline_name}: Enter Pipeline Line Loop", LOG_LEVEL.DEBUG
            )

            # This should block here
            self.__rmq_handler.start_consuming()

        except Exception:
            track_error = traceback.format_exc()
            self.logs.write_logs(
                f"Error-{self.pipeline_name}:{track_error}", LOG_LEVEL.ERROR
            )
        except KeyboardInterrupt:
            self.logs.write_logs(
                f"Pipeline {self.pipeline_name} interrupted by user", LOG_LEVEL.INFO
            )
        finally:
            # Cleanup
            self.__rmq_handler.close()
            if hasattr(self, "_executor"):
                self._executor.shutdown(wait=True)
        del models_manager

    # //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

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

    # //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    @property
    def No_Clients(self):
        return len(self.pipeline_clients)

    # //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    @property
    def stop(self):
        return self.__STOP.value

    @stop.setter
    def stop(self, state):
        self.__STOP.value = state


# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
# @property
# def PipeLine_OutOfMemory(self):
#     return self.__PipeLine_OutOfMemory.value
# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
