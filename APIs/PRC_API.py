import aiohttp
import asyncio

server_keys = {}

# Custom exceptions
class ServerLinkNotFound(Exception):
    pass

class ResponseFailed(Exception):
    detail: str | None
    code: int | None
    data: str

    def __init__(self, data: str, detail: str | None = None, code: int | None = None, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self) -> str:
        return f"ResponseFailed(data={self.data}, detail={self.detail}, code={self.code})"

class BaseModel:
    def __init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class ServerStatus(BaseModel):
    Name: str | None = None
    OwnerId: int | None = None
    CoOwnerIds: list[int] | None = None
    CurrentPlayers: int | None = None
    MaxPlayers: int | None = None
    JoinKey: str | None = None
    AccVerifiedReq: str = ""
    TeamBalance: bool = False

class ServerPlayers(BaseModel):
    Player: str | None
    Permission: str
    Callsign: str | None
    Team: str | None

class ServerJoinLogs(BaseModel):
    Join: bool
    Timestamp: int
    Player: str | None

class ServerQueue(BaseModel):
    total_players: int

class ServerKillLogs(BaseModel):
    killed: str | None
    timestamp: int
    killer: str | None

class ServerCommandLogs(BaseModel):
    player: str | None
    timestamp: int
    command: str | None

class ServerModCalls(BaseModel):
    caller: str | None
    moderator: str | None
    timestamp: int

class ServerBans(BaseModel):
    player_id: int

class ServerVehicles(BaseModel):
    texture: str | None
    name: str | None
    owner: str | None

class ServerCommand(BaseModel):
    command: str | None

# Main API class
class PRC_API:
    def __init__(self, bot, base_url: str, api_key: str):
        self.bot = bot
        self.base_url = base_url
        self.api_key = api_key
        self.session = aiohttp.ClientSession()

    async def fetch_server_key(self, server_id: int) -> str:
        if server_id not in server_keys:
            server = await self.bot.erlc_keys.find_one({"_id": server_id})
            if not server:
                raise ServerLinkNotFound("API Key not found")
            server_keys[server_id] = server["key"]
        return server_keys[server_id]

    async def _send_request(self, method: str, endpoint: str, server_id: int, **kwargs):
        server_key = await self.fetch_server_key(server_id)
        async with self.session.request(
            method, f"{self.base_url}/{endpoint}",
            headers={"Server-Key": server_key}, **kwargs
        ) as resp:
            data = await resp.json()
            if resp.status == 200:
                return data
            
            error_map = {
                429: "Rate limited",
                400: "Bad Request",
                403: "Unauthorized",
                422: "The private server has no players in it",
                500: "Problem communicating with Roblox",
            }
            detail = error_map.get(resp.status, "Unexpected Error")
            raise ResponseFailed(data, detail=detail, code=resp.status)

    async def _fetch_data(self, endpoint: str, server_id: int, model_class: type) -> list | object:
        data = await self._send_request("GET", endpoint, server_id)
        if isinstance(data, list):
            return [model_class(**item) for item in data]
        return model_class(**data)

    async def _fetch_server_status(self, server_id: int) -> ServerStatus:
        return await self._fetch_data("server", server_id, ServerStatus)

    async def _fetch_server_players(self, server_id: int) -> list[ServerPlayers]:
        return await self._fetch_data("server/players", server_id, ServerPlayers)

    async def _fetch_server_join_logs(self, server_id: int) -> list[ServerJoinLogs]:
        return await self._fetch_data("server/joinlogs", server_id, ServerJoinLogs)

    async def _fetch_server_queue(self, server_id: int) -> ServerQueue:
        return await self._fetch_data("server/queue", server_id, ServerQueue)

    async def _fetch_server_kill_logs(self, server_id: int) -> list[ServerKillLogs]:
        return await self._fetch_data("server/killlogs", server_id, ServerKillLogs)

    async def _fetch_server_command_logs(self, server_id: int) -> list[ServerCommandLogs]:
        return await self._fetch_data("server/commandlogs", server_id, ServerCommandLogs)

    async def _fetch_server_mod_calls(self, server_id: int) -> list[ServerModCalls]:
        return await self._fetch_data("server/modcalls", server_id, ServerModCalls)

    async def _fetch_server_bans(self, server_id: int) -> list[ServerBans]:
        return await self._fetch_data("server/bans", server_id, ServerBans)

    async def _fetch_server_vehicles(self, server_id: int) -> list[ServerVehicles]:
        return await self._fetch_data("server/vehicles", server_id, ServerVehicles)

    async def _send_command(self, server_id: int, command: str) -> ServerCommand:
        data = await self._send_request("POST", "server/command", server_id, json={"command": command})
        return ServerCommand(**data)

    async def _send_message_command(self, server_id: int, command: str):
        return await self._send_request("POST", "server/command", server_id, json={"command": f":m {command}"})

    async def fetch_all_server_data(self, server_id: int) -> dict:
        results = await asyncio.gather(
            self._fetch_server_status(server_id),
            self._fetch_server_players(server_id),
            self._fetch_server_join_logs(server_id),
            self._fetch_server_queue(server_id),
        )
        return {
            "status": results[0],
            "players": results[1],
            "join_logs": results[2],
            "queue": results[3],
        }

    async def close(self):
        await self.session.close()
