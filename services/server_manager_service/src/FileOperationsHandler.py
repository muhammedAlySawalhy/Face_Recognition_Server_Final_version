#!/usr/bin/env python3.10
import os
import time
import orjson
import io
import json
from typing import Dict, List
from common_utilities import Base_Thread, LOGGER, LOG_LEVEL, RedisHandler,write_json
from utilities import getServerDataDirectoryPath,get_available_users

class FileOperationsHandler(Base_Thread):
    """
    This class handles file read/write operations and client status management.
    It extends Base_Thread and manages file-based data operations.
    """

    def __init__(
        self,
        thread_name: str,
        redis_data: RedisHandler = None,
        logger = None
    ):
        """
        Initializes the FileOperationsHandler thread with necessary attributes.

        Args:
            thread_name (str): Name of the thread for logging and identification.
            redis_data (RedisHandler): Redis handler instance
            logger: Logger instance or string for logging
        """
        super().__init__(thread_name)
        
        # Initialize logging for the thread
        if isinstance(logger, str):
            self.logs = LOGGER(logger)
            self.logs.create_File_logger(f"{logger}", log_levels=["DEBUG", "ERROR", "CRITICAL", "WARNING"])
            self.logs.create_Stream_logger(log_levels=["INFO", "ERROR", "WARNING"])
        elif isinstance(logger, LOGGER):
            self.logs = logger
        else:
            self.logs = LOGGER(None)
        
        self.__redis_data = redis_data if redis_data else RedisHandler(db=0)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def run(self):
        """
        Main thread execution method that continuously updates client files.
        """
        self.thread_started = True
        try:
            self.logs.write_logs(f"Starting FileOperationsHandler thread", LOG_LEVEL.INFO)
            
            while not self.stop_thread:
                time.sleep(0.5)  # Introduce a delay to reduce CPU load
                # Perform various tasks related to client management and file updates
                self.update_pause_clients()
                self.update_blocked_clients()
                self.update_active_deactivate_clients()
                self.update_connect_to_internet()
                
        except Exception as e:
            import traceback
            track_error = traceback.format_exc()
            self.logs.write_logs(f"Error in FileOperationsHandler: {track_error}", LOG_LEVEL.ERROR)
        finally:
            self.logs.write_logs("FileOperationsHandler thread stopped", LOG_LEVEL.INFO)
        self.thread_started = False
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def update_pause_clients(self):
        """
        Updates the list of paused clients and saves it persistently.
        """
        # Load the list of paused clients, likely from a persistent data source or database
        paused_clients = self.__redis_data.get_dict("Clients_status").get("paused_clients",[])
        # Save the paused clients to a JSON file
        self.__save_paused_clients(paused_clients)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def update_blocked_clients(self):
        """
        Updates the list of blocked clients and saves it persistently.
        """
        # Load the list of blocked clients, likely from a persistent data source or database
        blocked_clients = self.__redis_data.get_dict("Clients_status").get("blocked_clients",[])
        self.__save_blocked_clients(blocked_clients)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def update_active_deactivate_clients(self):
        """
        Identifies deactivated clients and updates their status in the process data.
        """
        # Log the start of the 'update_active_deactivate_clients' process
        # self.logs.write_logs("Start 'update_active_deactivate_clients'",LOG_LEVEL.DEBUG)
        # Retrieve the current list of active clients from the process data
        clients_status=self.redis_data.get_dict("Clients_status")
        active_clients = clients_status.get("active_clients",[])
        # Retrieve the current list of available clients and convert it to a set for efficient operations
        available_clients = list(get_available_users())
        # Retrieve the current list of blocked clients and convert it to a set for efficient operations
        blocked_clients = clients_status.get("blocked_clients",[])
        # Determine the set of clients to deactivate:
        # - Clients that are in 'available_clients' but not in 'active_clients'
        # - Clients that are in both 'available_clients' and 'blocked_clients'
        deactivate_clients = set(available_clients) - set(active_clients) | set(available_clients) & set(blocked_clients)
        # Save the updated active clients data
        self.save_active_clients(active_clients)
        # Save the updated deactivate clients data
        self.save_deactivate_clients(list(deactivate_clients))
        
        self.redis_data.set_dict("Clients_status",{"deactivate_clients":list(deactivate_clients)})
    def update_active_deactivate_clients(self):
        """
        Identifies deactivated clients and updates their status in the process data.
        """
        # Retrieve the current list of active clients from the process data
        clients_status = self.__redis_data.get_dict("Clients_status")
        active_clients = clients_status.get("active_clients", [])
        blocked_clients = clients_status.get("blocked_clients",[])
        available_clients = list(get_available_users())
        deactivated_clients = set(available_clients) - set(active_clients) | set(available_clients) & set(blocked_clients)
        self.__redis_data.set_dict("Clients_status", {"deactivate_clients": list(deactivated_clients)})
        # Save the updated active clients data
        self.__save_active_clients(active_clients)
        # Save the updated deactivate clients data
        self.__save_deactivate_clients(deactivated_clients)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def update_connect_to_internet(self):
        """
        Updates the connect to internet error clients and saves it persistently.
        """
        clients_status = self.__redis_data.get_dict("Clients_status")
        connecting_internet_error = clients_status.get("connecting_internet_error", [])
        self.__save_connect_to_internet(connecting_internet_error)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __save_paused_clients(self, paused_clients):
        """
        Saves the list of active clients to a JSON file.
        """
        # Define the file path for the 'active_clients.json' file located in the 'Server_Data' directory under 'Data'
        Server_Data_path = getServerDataDirectoryPath()
        active_clients_file = os.path.join(
            Server_Data_path,
            "pause_clients.json"  # The filename for active clients data
        )
        # Write the sorted list of active clients to the JSON file
        write_json({"clients": sorted(paused_clients)}, active_clients_file)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __save_blocked_clients(self, blocked_clients):
        """
        Saves the list of active clients to a JSON file.
        """
        # Define the file path for the 'active_clients.json' file located in the 'Server_Data' directory under 'Data'
        Server_Data_path = getServerDataDirectoryPath()
        active_clients_file = os.path.join(
            Server_Data_path,
            "blocked_clients.json"  # The filename for active clients data
        )
        # Write the sorted list of active clients to the JSON file
        write_json({"clients": sorted(blocked_clients)}, active_clients_file)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __save_active_clients(self, active_clients):
        """
        Saves the list of active clients to a JSON file.
        """
        # Define the file path for the 'active_clients.json' file located in the 'Server_Data' directory under 'Data'
        Server_Data_path = getServerDataDirectoryPath()
        active_clients_file = os.path.join(
            Server_Data_path,
            "active_clients.json"  # The filename for active clients data
        )
        # Write the sorted list of active clients to the JSON file
        write_json({"clients": sorted(active_clients)}, active_clients_file)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __save_deactivate_clients(self, deactivate_clients):
        """
        Saves the list of deactivated clients to a JSON file.
        """
        # Define the file path for the 'deactivate_clients.json' file located in the 'Server_Data' directory under 'Data'
        Server_Data_path = getServerDataDirectoryPath()
        deactivate_clients_file = os.path.join(
            Server_Data_path,
            "deactivate_clients.json"  # The filename for deactivate clients data
        )
        # Write the sorted list of deactivate clients to the JSON file
        write_json({"clients": sorted(set(deactivate_clients))}, deactivate_clients_file)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __save_connect_to_internet(self, connect_to_internet):
        """
        Saves the list of clients with internet connection issues to a JSON file.
        """
        Server_Data_path = getServerDataDirectoryPath()
        connect_to_internet_file = os.path.join(
            Server_Data_path,
            "Network_Action.json"  # The filename for internet connection clients data
        )
        # Write the sorted list of connect to internet clients to the JSON file
        write_json({"clients": sorted(set(connect_to_internet))}, connect_to_internet_file)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
