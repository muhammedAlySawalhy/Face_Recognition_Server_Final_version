#!/usr/bin/env python3.10
"""
Pipeline Management Service
Based on PipeLinesManager.py from the original Scripts directory
"""
import sys
import os

# Add current service directory to Python path
service_root = os.path.dirname(os.path.abspath(__file__))
if service_root not in sys.path:
    sys.path.insert(0, service_root)

from src.PipeLinesManager import PipeLinesManager
from common_utilities import LOG_LEVEL
from utilities import full_system_initialization, get_environment_config
import time

def main():
    # Complete system initialization (paths, directories, Redis, logger)
    paths, pipeline_logger, _config_manager = full_system_initialization(
        __file__, "Pipeline_Service"
    )
    
    # Get environment configuration
    env_config = get_environment_config()    
    # Create Pipeline Manager
    pipe_lines_manager = PipeLinesManager(
        "PipeLinesManager",
        MaxPipeline=env_config["MaxPipeline"],
        MaxClientPerPipeline=env_config["MaxClientPerPipeline"],
        logger=pipeline_logger
    )
    
    pipeline_logger.write_logs("Starting Pipeline Management Service...", LOG_LEVEL.INFO)
    
    try:
        pipe_lines_manager.Start_process()
        pipeline_logger.write_logs(f"Pipeline Manager started with PID: {pipe_lines_manager.pid}", LOG_LEVEL.INFO)
        
        # Keep the service running and monitor health
        while True:
            time.sleep(1)
            if not pipe_lines_manager.is_alive():
                pipeline_logger.write_logs("Pipeline Manager died, restarting...", LOG_LEVEL.WARNING)
                pipe_lines_manager.Start_process()
                
    except KeyboardInterrupt:
        pipeline_logger.write_logs("Pipeline Management Service shutdown initiated by user", LOG_LEVEL.INFO)
        pipe_lines_manager.Stop_process()
        pipe_lines_manager.Join_process()
        pipeline_logger.write_logs("Pipeline Management Service stopped", LOG_LEVEL.INFO)
    except Exception as e:
        pipeline_logger.write_logs(f"Critical error in Pipeline Management Service: {e}", LOG_LEVEL.CRITICAL)
        import traceback
        pipeline_logger.write_logs(f"Traceback: {traceback.format_exc()}", LOG_LEVEL.CRITICAL)
    finally:
        try:
            if pipe_lines_manager.is_alive():
                pipe_lines_manager.terminate()
        except:
            pass

if __name__ == "__main__":
    main()
