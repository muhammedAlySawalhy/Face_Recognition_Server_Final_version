#!/usr/bin/env python3.10
"""
Decision Service - Action Decision Manager
Based on ActionDecisionManager_Process.py from the original Scripts directory
"""
import sys
import os

# Add current service directory to Python path
service_root = os.path.dirname(os.path.abspath(__file__))
if service_root not in sys.path:
    sys.path.insert(0, service_root)

from src.ActionDecisionManager_Process import ActionDecisionManager_Process
from common_utilities import LOG_LEVEL
from utilities.system_init import full_system_initialization
import time

def main():
    # Complete system initialization (paths, directories, Redis, logger)
    paths, decision_logger, storage_client = full_system_initialization("Decision_Service")
    decision_logger.write_logs(f"paths {paths}",LOG_LEVEL.INFO)
    # Create Action Decision Manager
    action_decision_manager = ActionDecisionManager_Process(
        process_name="ActionDecisionManager",
        logger=decision_logger,
        storage_client=storage_client,
    )
    
    decision_logger.write_logs("Starting Decision Service...", LOG_LEVEL.INFO)
    
    try:
        action_decision_manager.Start_process()
        decision_logger.write_logs(f"Decision Manager started with PID: {action_decision_manager.pid}", LOG_LEVEL.INFO)
        
        # Keep the service running and monitor health
        while True:
            time.sleep(1)
            if not action_decision_manager.is_alive():
                decision_logger.write_logs("Decision Manager died, restarting...", LOG_LEVEL.WARNING)
                action_decision_manager.Start_process()
                
    except KeyboardInterrupt:
        decision_logger.write_logs("Decision Service shutdown initiated by user", LOG_LEVEL.INFO)
        action_decision_manager.Stop_process()
        action_decision_manager.Join_process()
        decision_logger.write_logs("Decision Service stopped", LOG_LEVEL.INFO)
    except Exception as e:
        decision_logger.write_logs(f"Critical error in Decision Service: {e}", LOG_LEVEL.CRITICAL)
        import traceback
        decision_logger.write_logs(f"Traceback: {traceback.format_exc()}", LOG_LEVEL.CRITICAL)
    finally:
        try:
            if action_decision_manager.is_alive():
                action_decision_manager.terminate()
        except:
            pass

if __name__ == "__main__":
    main()
