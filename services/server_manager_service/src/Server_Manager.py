#!/usr/bin/env python3.10
from typing import Dict, List,Literal
import os
import time
import traceback
import threading
from common_utilities import Base_process, LOGGER,LOG_LEVEL,RedisHandler, Sync_RMQ, StorageClient
from .Save_Action_thread import SaveAction_Thread
from .FastAPIHandler import FastAPIHandler
from .FileOperationsHandler import FileOperationsHandler

class Server_Manager(Base_process):
    """
    This class manages server-side operations related to client assignment, file updates,
    and threading for handling concurrent tasks. It extends Base_process and leverages
    utility methods for logging and JSON processing.
    """

    def __init__(
        self,
        process_name: str,
        gui_backend_ip: str = "0.0.0.0",
        gui_backend_port: int = 6000,
        logger = None,
        storage_client: StorageClient | None = None,
        **kwargs
    ):
        """
        Initializes the Server_Manager object with necessary attributes, threads, and logging.

        Args:
            process_name (str): Name of the process for logging and identification.
            gui_backend_ip (str): IP address for the GUI backend
            gui_backend_port (int): Port for the GUI backend
            logger: Logger instance or string for logging
        """
        # Call the base class constructor to initialize the process with a name and arguments
        super().__init__(process_name)
        # Initialize logging for the process
        if isinstance(logger,str):
            self.logs = LOGGER(logger)
            self.logs.create_File_logger(f"{logger}",log_levels=["DEBUG","ERROR", "CRITICAL", "WARNING"])
            self.logs.create_Stream_logger(log_levels=["INFO", "ERROR", "WARNING"])
        elif isinstance(logger,LOGGER):
            self.logs=logger
        else:
            self.logs = LOGGER(None)
        
        # Initialize Redis handler
        if redis_data := kwargs.get("redis_data", None):
            self.__redis_data = redis_data
        else:
            self.__redis_data=RedisHandler(db=0)
        
        self.storage_client = storage_client or kwargs.get("storage_client")

        # Initialize RMQ handler for saved_actions
        self.__rmq_handler = Sync_RMQ(logger=self.logs)
        # Configure RMQ for better memory management
        self.__rmq_handler.max_retries = 3
        self.__rmq_handler.retry_delay = 1
        self.__rmq_handler.prefetch_count = 1  # Limit concurrent processing
        self.__rmq_handler.durable_queues = True  # Ensure queue durability
        self.__rmq_handler.persistent_messages = False  # Don't persist messages to reduce disk usage
        
        # Store configuration for thread restart purposes
        self.__gui_backend_ip = gui_backend_ip
        self.__gui_backend_port = gui_backend_port
        
        # Initialize SaveAction_Thread
        self.save_action_thread: SaveAction_Thread = SaveAction_Thread(
            "SaveAction_Thread",
            storage_client=self.storage_client,
        )
        
        # Initialize FastAPI handler thread
        self.fastapi_handler:FastAPIHandler = FastAPIHandler(
            thread_name="FastAPIHandler_Thread",
            gui_backend_ip=gui_backend_ip,
            gui_backend_port=gui_backend_port,
            redis_data=self.__redis_data,
            logger=self.logs
        )
        
        # Initialize File Operations handler thread
        self.file_ops_handler:FileOperationsHandler = FileOperationsHandler(
            thread_name="FileOperationsHandler_Thread",
            redis_data=self.__redis_data,
            logger=self.logs
        )
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def setup_RMQ(self):
        """Setup RMQ for consuming saved_actions queue"""
        retries = int(os.getenv("RMQ_SETUP_RETRIES", "10"))
        delay = float(os.getenv("RMQ_SETUP_DELAY_SECONDS", "3"))
        for attempt in range(1, retries + 1):
            try:
                # Create consumer for saved_actions
                self.__rmq_handler.create_producer()
                self.__rmq_handler.create_consumer()
                self.__rmq_handler.create_queues("saved_actions")
                self.logs.write_logs(
                    "RMQ setup for saved_actions completed", LOG_LEVEL.DEBUG
                )
                return
            except Exception as e:
                self.logs.write_logs(
                    f"Error setting up RMQ for saved_actions (attempt {attempt}/{retries}): {e}",
                    LOG_LEVEL.WARNING if attempt < retries else LOG_LEVEL.ERROR,
                )
                if attempt >= retries:
                    raise
                time.sleep(delay)

#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def _restart_fastapi_handler(self):
        """Helper method to restart the FastAPI handler thread"""
        try:
            self.logs.write_logs("Attempting to restart FastAPI handler...", LOG_LEVEL.DEBUG)
            
            # Stop the old thread if it exists and is running
            if hasattr(self, 'fastapi_handler') and self.fastapi_handler:
                if self.fastapi_handler.is_started():
                    self.logs.write_logs("Stopping existing FastAPI handler thread...", LOG_LEVEL.DEBUG)
                    self.fastapi_handler.Stop_thread()
                    self.fastapi_handler.Join_thread()
                
            # Create a new FastAPI handler instance
            self.logs.write_logs("Creating new FastAPI handler instance...", LOG_LEVEL.DEBUG)
            self.fastapi_handler = FastAPIHandler(
                thread_name="FastAPIHandler_Thread",
                gui_backend_ip=self.__gui_backend_ip,
                gui_backend_port=self.__gui_backend_port,
                redis_data=self.__redis_data,
                logger=self.logs
            )
            
            # Start the new thread
            self.logs.write_logs("Starting new FastAPI handler thread...", LOG_LEVEL.DEBUG)
            self.fastapi_handler.Start_thread()
            self.logs.write_logs("FastAPI handler thread restarted successfully", LOG_LEVEL.INFO)
        except Exception as e:
            import traceback
            track_error = traceback.format_exc()
            self.logs.write_logs(f"Failed to restart FastAPI handler: {e}\n{track_error}", LOG_LEVEL.ERROR)

    def _restart_file_ops_handler(self):
        """Helper method to restart the File Operations handler thread"""
        try:
            self.logs.write_logs("Attempting to restart File operations handler...", LOG_LEVEL.DEBUG)
            
            # Stop the old thread if it exists and is running
            if hasattr(self, 'file_ops_handler') and self.file_ops_handler:
                if self.file_ops_handler.is_started():
                    self.logs.write_logs("Stopping existing File operations handler thread...", LOG_LEVEL.DEBUG)
                    self.file_ops_handler.Stop_thread()
                    self.file_ops_handler.Join_thread()
                
            # Create a new File Operations handler instance
            self.logs.write_logs("Creating new File operations handler instance...", LOG_LEVEL.DEBUG)
            self.file_ops_handler = FileOperationsHandler(
                thread_name="FileOperationsHandler_Thread",
                redis_data=self.__redis_data,
                logger=self.logs
            )
            
            # Start the new thread
            self.logs.write_logs("Starting new File operations handler thread...", LOG_LEVEL.DEBUG)
            self.file_ops_handler.Start_thread()
            self.logs.write_logs("File operations handler thread restarted successfully", LOG_LEVEL.INFO)
        except Exception as e:
            import traceback
            track_error = traceback.format_exc()
            self.logs.write_logs(f"Failed to restart File operations handler: {e}\n{track_error}", LOG_LEVEL.ERROR)

#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def setup_consumer(self):
            @self.__rmq_handler.consume_messages(queue_name="saved_actions")
            def process_saved_actions(payload):
                try:
                    self.logs.write_logs(f"Processing saved action for user: {payload.get('user_name', 'unknown')}", LOG_LEVEL.DEBUG)
                    
                    user_name = payload.get("user_name")
                    action_reason = payload.get("Action_Reason")
                    action_image = payload.get("Action_image")
                    action_object_key = payload.get("action_image_object_key")
                    action_bucket = payload.get("action_image_bucket")
                    
                    if user_name and action_reason:
                        # Use the SaveAction_Thread for saving
                        self.save_action_thread.add_to_queue(
                            user_name,
                            action_reason,
                            action_image,
                            action_object_key,
                            action_bucket,
                        )
                        self.logs.write_logs(
                            f"Queued action for saving for user {user_name} (object_key={action_object_key})",
                            LOG_LEVEL.DEBUG,
                        )
                    else:
                        self.logs.write_logs(f"Invalid saved_action payload: missing required fields", LOG_LEVEL.WARNING)
                        
                except Exception as e:
                    import traceback
                    track_error = traceback.format_exc()
                    self.logs.write_logs(f"Error processing saved action: {e}\n{track_error}", LOG_LEVEL.ERROR)

#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def run(self):
        """
        Starts all threads for file updates, client assignment management, and user handling.
        Ensures proper thread lifecycle management during process runtime.
        """
        self.logs.write_logs(f"Start 'Server_Manager' Process With ID:{self.pid}",LOG_LEVEL.DEBUG)
        self.logs.write_logs(f"Server Manager is ready!",LOG_LEVEL.INFO)
        try:
            # Start SaveAction_Thread
            self.save_action_thread.Start_thread()
            
            # Setup RMQ for saved_actions
            self.setup_RMQ()
            self.setup_consumer()
            
            time.sleep(0.15)  # Introduce a small delay to reduce CPU spinning and allow smooth thread initialization
            
            # Start threads with proper error handling
            try:
                self.logs.write_logs("Attempting to start FastAPI handler thread...", LOG_LEVEL.DEBUG)
                if self.fastapi_handler.is_started():
                    self.logs.write_logs("FastAPI handler thread is already running, skipping start", LOG_LEVEL.WARNING)
                else:
                    self.fastapi_handler.Start_thread()
                    self.logs.write_logs("FastAPI handler thread started successfully", LOG_LEVEL.INFO)
            except Exception as e:
                self.logs.write_logs(f"Failed to start FastAPI handler: {e}", LOG_LEVEL.ERROR)
                self._restart_fastapi_handler()
            
            try:
                self.logs.write_logs("Attempting to start File operations handler thread...", LOG_LEVEL.DEBUG)
                if self.file_ops_handler.is_started():
                    self.logs.write_logs("File operations handler thread is already running, skipping start", LOG_LEVEL.WARNING)
                else:
                    self.file_ops_handler.Start_thread()
                    self.logs.write_logs("File operations handler thread started successfully", LOG_LEVEL.INFO)
            except Exception as e:
                self.logs.write_logs(f"Failed to start File operations handler: {e}", LOG_LEVEL.ERROR)
                self._restart_file_ops_handler()
            
            # Start saved_actions consumer in a separate thread
            rmq_thread = threading.Thread(target=self.__rmq_handler.start_consuming, name="rmq_consumer_thread", daemon=True)
            rmq_thread.start()

            # Keep the main process alive and monitor threads
            while not self.stop_process:
                time.sleep(1)
                
                # Check if threads are alive and restart if needed
                if not self.fastapi_handler.is_started():
                    self.logs.write_logs("FastAPI handler thread died, restarting...", LOG_LEVEL.WARNING)
                    self._restart_fastapi_handler()

                if not self.file_ops_handler.is_started():
                    self.logs.write_logs("File operations handler thread died, restarting...", LOG_LEVEL.WARNING)
                    self._restart_file_ops_handler()
                    
        except KeyboardInterrupt:
            pass
        except Exception:
            track_error=traceback.format_exc()
            self.logs.write_logs(f"Error-{self.process_name}:{track_error}",LOG_LEVEL.ERROR)
        finally:
            # Cleanup threads
            try:
                # Stop FastAPI handler thread
                if hasattr(self, 'fastapi_handler'):
                    self.fastapi_handler.Stop_thread()
                    self.fastapi_handler.Join_thread()
                    
                # Stop File operations handler thread
                if hasattr(self, 'file_ops_handler'):
                    self.file_ops_handler.Stop_thread()
                    self.file_ops_handler.Join_thread()
                    
                # Stop SaveAction_Thread
                if hasattr(self, 'save_action_thread'):
                    self.save_action_thread.Stop_thread()
                    self.save_action_thread.Join_thread()
            except Exception as e:
                self.logs.write_logs(f"Error stopping threads: {e}", LOG_LEVEL.ERROR)
            
            # Cleanup RMQ connections
            try:
                self.__rmq_handler.close()
            except Exception as e:
                self.logs.write_logs(f"Error closing RMQ connections: {e}", LOG_LEVEL.ERROR)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
if __name__=="__main__":
    import os
    # ---------------------------------------------------------------------------#
    redis = RedisHandler()
    redis.clear()
    redis.set_value("SYSTEM_FULL",0)
    redis.set_value("GPUs_FULL",0)
    redis.set_dict("Clients_status", {
        "active_clients": list(),
        "deactivate_clients": list(),
        "blocked_clients": list(),
        "paused_clients": list(),
        "connecting_internet_error": list(),
        "clients_to_close": list(),
    })
    # ---------------------------------------------------------------------------#
    server_manager=Server_Manager("Server_Files_Handler",logger="Server_Files_Handler_logs")
    # ---------------------------------------------------------------------------#
    try:
        server_manager.Start_process()
        while (1):
            time.sleep(1)
            if not server_manager.is_started():
                server_manager.Start_process()
    except KeyboardInterrupt:
        server_manager.Stop_process()
        server_manager.Join_process()
