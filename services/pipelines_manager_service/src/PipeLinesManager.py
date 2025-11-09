#!/usr/bin/env python3.10
from typing import Dict
import asyncio
from common_utilities import Base_process, LOGGER, LOG_LEVEL, Async_RMQ


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
        self._rmq = Async_RMQ(logger=self.logs)

    def _select_pipeline(self) -> int:
        pipeline_id = self._next_pipeline
        self._next_pipeline = (self._next_pipeline + 1) % self.num_pipelines
        if (
            self.max_clients_per_pipeline > 0
            and self.pipeline_message_counts[pipeline_id] >= self.max_clients_per_pipeline
        ):
            self.logs.write_logs(
                f"Pipeline {pipeline_id} load {self.pipeline_message_counts[pipeline_id]} "
                f"exceeds configured capacity {self.max_clients_per_pipeline}",
                LOG_LEVEL.WARNING,
            )
        return pipeline_id

    async def _push_data_to_pipeline(self, data: dict) -> None:
        pipeline_id = self._select_pipeline()
        self.pipeline_message_counts[pipeline_id] += 1
        self.logs.write_logs(
            f"Routing payload to pipeline {pipeline_id}",
            LOG_LEVEL.DEBUG,
        )
        await self._rmq.publish_data(
            data,
            queue_name=f"PipeLine_{pipeline_id}",
            routing_key=f"PipeLine_{pipeline_id}",
            exchange_name="received_clients_data",
        )

    def _register_consumers(self):
        @self._rmq.consume_messages(queue_name="clients_data")
        async def client_handler(payload):
            if not isinstance(payload, dict):
                self.logs.write_logs(
                    f"Ignoring non-dict payload on clients_data: type={type(payload).__name__}",
                    LOG_LEVEL.WARNING,
                )
                return
            identifier = payload.get("client_name") or payload.get("user_name")
            if not identifier:
                self.logs.write_logs(
                    f"Discarding payload without client identifier: keys={list(payload.keys())}",
                    LOG_LEVEL.ERROR,
                )
                return
            await self._push_data_to_pipeline(payload)

    async def _run_async(self):
        await self._rmq.create_consumer()
        await self._rmq.create_producer(
            exchange_name="received_clients_data", exchange_type="direct"
        )
        await self._rmq.create_queues("clients_data")
        self._register_consumers()
        try:
            await self._rmq.start_consuming()
        finally:
            await self._rmq.close()

    def run(self):
        asyncio.run(self._run_async())
