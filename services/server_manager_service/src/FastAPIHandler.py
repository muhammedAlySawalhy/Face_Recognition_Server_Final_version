#!/usr/bin/env python3.10
import os
import time
from typing import Literal
from fastapi import FastAPI, HTTPException, Body
from fastapi.routing import APIRouter
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from common_utilities import Base_Thread, LOGGER, LOG_LEVEL, RedisHandler
from utilities import KeysRequest

class FastAPIHandler(Base_Thread):
    """
    This class handles FastAPI endpoints and web server operations.
    It extends Base_Thread and manages HTTP API operations.
    """

    def __init__(
        self,
        thread_name: str,
        gui_backend_ip: str = "0.0.0.0", 
        gui_backend_port: int = 6000,
        redis_data: RedisHandler = None,
        logger = None
    ):
        """
        Initializes the FastAPIHandler thread with necessary attributes.

        Args:
            thread_name (str): Name of the thread for logging and identification.
            gui_backend_ip (str): IP address for the GUI backend
            gui_backend_port (int): Port for the GUI backend
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
        
        self.__gui_backend_ip = gui_backend_ip
        self.__gui_backend_port = gui_backend_port
        self.__redis_data = redis_data if redis_data else RedisHandler(db=0)
        origin_url = os.getenv("GUI_ORIGIN_URL", "http://localhost:3000")
        # Initialize FastAPI app
        self.app = FastAPI()
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=[f"{origin_url}"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Setup routes during initialization
        self.__setup_routes()
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def __setup_routes(self):
        """
        Sets up the FastAPI routes for the server manager.
        """
        # Load server name from environment variables, defaulting to "default" if not set
        SERVER_NAME = os.getenv("SERVER_NAME", "default")
        # Create a router with a prefix based on the server name
        router = APIRouter()

        @router.post("/redis/get")
        async def get_from_redis(request: KeysRequest):
            if not request.keys:
                raise HTTPException(status_code=400, detail="No keys provided")
            clients_status: dict = self.__redis_data.get_dict("Clients_status")
            self.logs.write_logs(f"[/redis/get]Current clients_status: {clients_status}", LOG_LEVEL.DEBUG)
            results = []
            for key in request.keys:
                if key in clients_status:
                    results.append({key: clients_status[key]})
                else:
                    raise HTTPException(status_code=404, detail=f"Key '{key}' not found")
            return {"server": SERVER_NAME, "data": results}

        @router.post("/client/status/update")
        def update_client_status(
            username: str = Body(..., embed=True),
            status: Literal["normal","pause", "block"] = Body(..., embed=True)
        ):
            """
            Set user's status to 'pause' or 'block'.
            - If transitioning, pop from the previous state and push into the target state.
            - If first time (normal), simply push into the target state.
            """
            key_map = {
                "pause": "paused_clients",
                "block": "blocked_clients",
                "normal": "normal"
            }
            if status not in key_map:
                raise HTTPException(status_code=400, detail="Invalid status. Use 'pause' or 'block'.")
            target_key = key_map[status]
            try:
                clients_status: dict = self.__redis_data.get_dict("Clients_status") or {}
                self.logs.write_logs(f"[/client/status/update]Current clients_status: {clients_status}", LOG_LEVEL.DEBUG)

                paused_clients: list = list(clients_status.get("paused_clients", []))
                blocked_clients: list = list(clients_status.get("blocked_clients", []))
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Redis error: {str(e)}")

            # Detect previous status
            prev_status: Literal["normal", "pause", "block"]
            if username in paused_clients:
                prev_status = "pause"
            elif username in blocked_clients:
                prev_status = "block"
            else:
                prev_status = "normal"

            # If already in target state and not in the other state, nothing to do
            if prev_status == status:
                return {
                    "success": False,
                    "message": f"{username} already in {status} clients.",
                }

            # Pop from previous state if present
            if username in paused_clients:
                paused_clients = [u for u in paused_clients if u != username]
            if username in blocked_clients:
                blocked_clients = [u for u in blocked_clients if u != username]

            # Push to target state
            if target_key == "paused_clients":
                paused_clients.append(username)
            elif target_key == "blocked_clients":
                blocked_clients.append(username)

            # Persist both lists atomically (overwrite the whole dict to be safe)
            clients_status["paused_clients"] = list(set(paused_clients))  # Ensure unique entries
            clients_status["blocked_clients"] = list(set(blocked_clients))  # Ensure unique entries
            try:
                self.__redis_data.set_dict("Clients_status", clients_status)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Redis error: {str(e)}")

            return {
                "success": True,
                "message": f"{username} moved from {prev_status} to {status}.",
                "prev_status": prev_status,
                "new_status": status,
                "data": {
                    "paused_clients": paused_clients,
                    "blocked_clients": blocked_clients
                }
            }

        
        # Include the router in the FastAPI app
        self.app.include_router(router)
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    def run(self):
        """
        Main thread execution method that starts the FastAPI server.
        """
        self.thread_started = True
        try:
            self.logs.write_logs(f"Starting FastAPI server on {self.__gui_backend_ip}:{self.__gui_backend_port}", LOG_LEVEL.INFO)
            # Start the FastAPI server using uvicorn
            uvicorn.run(
                self.app, 
                host=self.__gui_backend_ip, 
                port=self.__gui_backend_port, 
                reload=False
            )
            
        except Exception as e:
            import traceback
            track_error = traceback.format_exc()
            self.logs.write_logs(f"Error in FastAPIHandler: {track_error}", LOG_LEVEL.ERROR)
        finally:
            self.logs.write_logs("FastAPIHandler thread stopped", LOG_LEVEL.INFO)
        self.thread_started = False
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
