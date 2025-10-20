#!/usr/bin/env python3.10
"""
Management Service - Server Manager
Based on Server_Manager.py from the original Scripts directory
"""
import sys
import os

# Add current service directory to Python path
service_root = os.path.dirname(os.path.abspath(__file__))
if service_root not in sys.path:
    sys.path.insert(0, service_root)

from src.Server_Manager import Server_Manager
from common_utilities import LOG_LEVEL
from utilities.system_init import full_system_initialization,get_environment_config
import time

def main():
    # Complete system initialization (paths, directories, Redis, logger)
    paths, management_logger = full_system_initialization(__file__, "Management_Service" )
    # Get environment configuration
    env_config = get_environment_config()
    # Create Server Manager
    server_manager = Server_Manager(
        "Server_Files_Handler",
        gui_backend_ip=env_config["GUI_BACKEND_IP"],
        gui_backend_port=env_config["GUI_BACKEND_PORT"],
        logger=management_logger
    )
    
    management_logger.write_logs("Starting Management Service...", LOG_LEVEL.INFO)
    
    try:
        server_manager.Start_process()
        management_logger.write_logs(f"Server Manager started with PID: {server_manager.pid}", LOG_LEVEL.INFO)
        
        # Keep the service running and monitor health
        while True:
            time.sleep(1)
            if not server_manager.is_alive():
                management_logger.write_logs("Server Manager died, restarting...", LOG_LEVEL.WARNING)
                server_manager.Start_process()
                
    except KeyboardInterrupt:
        management_logger.write_logs("Management Service shutdown initiated by user", LOG_LEVEL.INFO)
        server_manager.Stop_process()
        server_manager.Join_process()
        management_logger.write_logs("Management Service stopped", LOG_LEVEL.INFO)
    except Exception as e:
        management_logger.write_logs(f"Critical error in Management Service: {e}", LOG_LEVEL.CRITICAL)
        import traceback
        management_logger.write_logs(f"Traceback: {traceback.format_exc()}", LOG_LEVEL.CRITICAL)
    finally:
        try:
            if server_manager.is_alive():
                server_manager.terminate()
        except:
            pass

if __name__ == "__main__":
    main()
