#!/usr/bin/env python3.10
"""
Processing Service - Pipeline Workers
Based on PipeLine.py from the original Scripts directory
"""

import os
from common_utilities import LOG_LEVEL
from utilities import full_system_initialization, get_environment_config
import time
from src import PipeLine


def main():
    # Get pipeline configuration from environment
    pipeline_id = int(os.getenv("PIPELINE_ID", 0))

    # Complete system initialization
    (
        paths,
        models_parameters,
        worker_logger,
        _config_manager,
        storage_client,
    ) = full_system_initialization(__file__, f"Pipeline_Worker_{pipeline_id}")

    # Get environment configuration
    env_config = get_environment_config()

    # Create Pipeline
    pipeline = PipeLine(
        f"PipeLine_{pipeline_id}",
        Max_clients=env_config["MaxClientPerPipeline"],
        models_init_parameters=models_parameters,
        logger=worker_logger,
        storage_client=storage_client,
    )

    worker_logger.write_logs(
        f"Starting Processing Service Pipeline {pipeline_id}...", LOG_LEVEL.INFO
    )

    try:
        pipeline.Start_process()
        worker_logger.write_logs(
            f"Pipeline {pipeline_id} started with PID: {pipeline.pid}", LOG_LEVEL.INFO
        )

        # Keep the service running and monitor health
        while True:
            time.sleep(1)
            if not pipeline.is_alive():
                worker_logger.write_logs(
                    f"Pipeline {pipeline_id} died, restarting...", LOG_LEVEL.WARNING
                )
                pipeline.Start_process()

    except KeyboardInterrupt:
        worker_logger.write_logs(
            f"Processing Service Pipeline {pipeline_id} shutdown initiated by user",
            LOG_LEVEL.INFO,
        )
        pipeline.Stop_process()
        pipeline.Join_process()
        worker_logger.write_logs(
            f"Processing Service Pipeline {pipeline_id} stopped", LOG_LEVEL.INFO
        )
    except Exception as e:
        worker_logger.write_logs(
            f"Critical error in Processing Service Pipeline {pipeline_id}: {e}",
            LOG_LEVEL.CRITICAL,
        )
        import traceback

        worker_logger.write_logs(
            f"Traceback: {traceback.format_exc()}", LOG_LEVEL.CRITICAL
        )
    finally:
        try:
            if pipeline.is_alive():
                pipeline.terminate()
        except:
            pass


if __name__ == "__main__":
    main()
