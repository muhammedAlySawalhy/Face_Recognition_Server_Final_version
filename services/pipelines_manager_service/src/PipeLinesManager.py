#!/usr/bin/env python3.10
from typing import Dict

from common_utilities import Base_process, LOGGER, LOG_LEVEL, Sync_RMQ
import time
import traceback


class PipeLinesManager(Base_process):
    def __init__(
        self,
        manager_name: str,
        MaxClientPerPipeline: int,
        MaxPipeline: int,
        logger=None,
    ):
        super().__init__(manager_name, None)
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

        self.max_clients_per_pipeline = MaxClientPerPipeline
        self.num_pipelines = MaxPipeline

        self.pipeline_message_counts: Dict[int, int] = {
            pipeline_id: 0 for pipeline_id in range(self.num_pipelines)
        }
        self._next_pipeline = 0

        self.__rmq_handler = Sync_RMQ(logger=self.logs)
        self.__rmq_handler.max_retries = 3
        self.__rmq_handler.retry_delay = 1
        self.__rmq_handler.prefetch_count = 1
        self.__rmq_handler.durable_queues = True
        self.__rmq_handler.persistent_messages = False

    # ////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def Manager(self):
        try:
            time.sleep(0.1)
        except Exception:  # pylint: disable=broad-except
            track_error = traceback.format_exc()
            self.logs.write_logs(
                f"Error-{self.process_name}:{track_error}", LOG_LEVEL.ERROR
            )

    # ////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def Stop_process(self):
        super().Stop_process()

    # ////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __select_pipeline(self) -> int:
        pipeline_id = self._next_pipeline
        self._next_pipeline = (self._next_pipeline + 1) % self.num_pipelines
        self.logs.write_logs(
            f"Routing next payload to pipeline {pipeline_id}",
            LOG_LEVEL.DEBUG,
        )
        return pipeline_id

    # ////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __push_data_to_pipeline(self, client_name: str, data: dict) -> None:
        pipeline_id = self.__select_pipeline()
        self.pipeline_message_counts[pipeline_id] += 1
        self.__rmq_handler.publish_data(
            data,
            routing_key=f"PipeLine_{pipeline_id}",
            exchange_name="received_clients_data",
        )

    # ////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __setup_consumers(self) -> None:
        @self.__rmq_handler.consume_messages(queue_name="clients_data")
        def get_clients_data(payload):
            client_data: dict = payload
            if not isinstance(client_data, dict):
                self.logs.write_logs(
                    f"Ignoring non-dict payload on clients_data: type={type(client_data).__name__}",
                    LOG_LEVEL.WARNING,
                )
                return

            client_name = client_data.get("client_name") or client_data.get("user_name")
            if not client_name:
                self.logs.write_logs(
                    f"Discarding payload without client identifier: keys={list(client_data.keys())}",
                    LOG_LEVEL.ERROR,
                )
                return

            client_name = str(client_name).lower()
            self.__push_data_to_pipeline(client_name, client_data)

    # ////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __setupRMQ(self) -> None:
        self.__rmq_handler.create_consumer()
        self.__rmq_handler.create_producer(
            exchange_name="received_clients_data", exchange_type="direct"
        )
        self.__rmq_handler.create_queues("clients_data")
        self.__setup_consumers()

    # ////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def run(self):
        self.__setupRMQ()
        self.logs.write_logs(
            f"Start 'PipelinesManager' Process With ID:{self.pid}", LOG_LEVEL.DEBUG
        )
        self.logs.write_logs("Pipeline Manager is ready!", LOG_LEVEL.INFO)
        try:
            self.__rmq_handler.start_consuming()
        except KeyboardInterrupt:
            pass
        except Exception:  # pylint: disable=broad-except
            track_error = traceback.format_exc()
            self.logs.write_logs(
                f"Error-{self.process_name}:{track_error}", LOG_LEVEL.ERROR
            )
        self.logs.write_logs("Pipeline Manager is Closed!", LOG_LEVEL.INFO)
