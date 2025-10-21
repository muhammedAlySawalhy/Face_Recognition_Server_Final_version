
import websockets.asyncio
import websockets.asyncio.server
import json
from utilities.files_handler import get_available_users
from utilities.Datatypes import Action, Reason
from common_utilities import LOGGER, LOG_LEVEL

class ClientChecks:
    def __init__(self, logger):
        self.logs: LOGGER = logger

    # ------------------------------------------------------------------------------------------------------------------#
    async def client_is_paused(
        self,
        websocket: websockets.asyncio.server.ServerConnection,
        client_name: str,
        paused_clients: set,
    ) -> bool:
        if client_name in paused_clients:
            await websocket.send(
                json.dumps(
                    {
                        "action": Action.ACTION_WARNING.value,
                        "reason": Reason.REASON_PAUSED_CLIENT.value,
                    }
                )
            )
            return True
        return False

    # //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    async def client_is_blocked(
        self,
        websocket: websockets.asyncio.server.ServerConnection,
        client_name: str,
        blocked_clients: set,
    ) -> bool:
        if client_name in blocked_clients:
            await websocket.send(
                json.dumps(
                    {
                        "action": Action.ACTION_ERROR.value,
                        "reason": Reason.REASON_BLOCKED_CLIENT.value,
                    }
                )
            )
            self.logs.write_logs(f"Connection Closed: {client_name} blocked", LOG_LEVEL.INFO)
            await websocket.close()
            return True
        else:
            return False

    # //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    async def client_is_available(
        self,
        websocket: websockets.asyncio.server.ServerConnection,
        client_name: str,
        active_clients: set) -> bool:
        if client_name in list(get_available_users()):
            # check active_clients
            await self.add_to_active_clients(client_name, active_clients)
            #######################################
            return True
        else:
            await websocket.send(
                json.dumps(
                    {
                        "action": Action.ACTION_ERROR.value,
                        "reason": Reason.REASON_CLIENT_NOT_AVAILABLE.value,
                    }
                )
            )
            self.logs.write_logs(
                f"Connection Closed: not available clients with name '{client_name}'", LOG_LEVEL.ERROR
            )
            await websocket.close()
            return False

    # //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
    async def add_to_active_clients(
        self, client_name: str, active_clients: list | set):
        if client_name not in active_clients:
            if isinstance(active_clients, set):
                active_clients.add(client_name)
            else:
                active_clients.append(client_name)

# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

