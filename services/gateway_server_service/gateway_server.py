#!/usr/bin/env python3.10
"""
Gateway Service - WebSocket Server
Based on Server.py from the original Scripts directory
"""

import sys
import os

# Add current service directory to Python path
service_root = os.path.dirname(os.path.abspath(__file__))
if service_root not in sys.path:
    sys.path.insert(0, service_root)

from src.Server import Server
from common_utilities import LOG_LEVEL
from utilities.system_init import full_system_initialization, get_environment_config
import time


def main():
    # Complete system initialization (paths, directories, Redis, logger)
    paths, gateway_logger, config_manager, storage_client = full_system_initialization(
        __file__, "Gateway_Service"
    )

    # Get environment configuration
    env_config = get_environment_config()

    # Create and start gateway server
    server = Server(
        process_name="Gateway_Server",
        serve_ip=env_config["SERVER_IP"],
        server_port=env_config["SERVER_PORT"],
        endpoint_path=env_config["ENDPOINT_PATH"],
        logger=gateway_logger,
        config_manager=config_manager,
        rate_limiter_config={
            "max_clients": env_config["RATE_LIMIT_MAX_CLIENTS"],
            "window_size_in_millis": env_config["RATE_LIMIT_WINDOW_MS"],
            "cleanup_interval_in_millis": env_config["RATE_LIMIT_CLEANUP_MS"],
        },
        storage_client=storage_client,
    )

    gateway_logger.write_logs("Starting Gateway Service...", LOG_LEVEL.INFO)

    try:
        server.Start_process()
        gateway_logger.write_logs(
            f"Gateway Server started with PID: {server.pid}", LOG_LEVEL.INFO
        )

        # Keep the service running and monitor health
        while True:
            time.sleep(1)
            if not server.is_alive():
                gateway_logger.write_logs(
                    "Gateway Server died, restarting...", LOG_LEVEL.WARNING
                )
                server.Start_process()

    except KeyboardInterrupt:
        gateway_logger.write_logs(
            "Gateway Service shutdown initiated by user", LOG_LEVEL.INFO
        )
        server.Stop_process()
        server.Join_process()
        gateway_logger.write_logs("Gateway Service stopped", LOG_LEVEL.INFO)
    except Exception as e:
        gateway_logger.write_logs(
            f"Critical error in Gateway Service: {e}", LOG_LEVEL.CRITICAL
        )
        import traceback

        gateway_logger.write_logs(
            f"Traceback: {traceback.format_exc()}", LOG_LEVEL.CRITICAL
        )
    finally:
        try:
            if server.is_alive():
                server.terminate()
        except:
            pass


if __name__ == "__main__":
    main()
