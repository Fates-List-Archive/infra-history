from ..core import *
from modules.models.ws_api import *

router = APIRouter(
    include_in_schema = True,
    tags = ["Websocket API"]
) # No arguments needed for websocket but keep for chat

bootstrap_info = {
    "versions": ["v1"],
    "endpoints": {
        "v1": {
            "bot_realtime_stats": "/api/v1/ws/bot/rtstats",
            "chat": "/api/v1/ws/chat"
        }
    }
}

@router.get("/api/ws", response_model = Bootstrap, dependencies=[Depends(RateLimiter(times=5, minutes=1))])
async def websocket_bootstrap(request: Request):
    """
        This is the gateway for all websockets. Use this to find which route you need or whether it is available
    """
    return bootstrap_info

@router.websocket("/api/v1/ws/bot/rtstats")
async def websocket_bot_rtstats_v1(websocket: WebSocket):
    await manager.connect(websocket)
    if websocket.api_token == []:
        await manager.send_personal_message({"payload": "IDENTITY", "type": "API_TOKEN"}, websocket)
        try:
            api_token = await websocket.receive_json()
            print("HERE")
            if api_token.get("payload") != "IDENTITY_RESPONSE" or api_token.get("type") != "API_TOKEN":
                raise TypeError
        except:
            await manager.send_personal_message({"payload": "KILL_CONN", "type": "INVALID_IDENTITY_RESPONSE"}, websocket)
            return await ws_close(websocket, 4004)
        api_token = api_token.get("data")
        if api_token is None or type(api_token) == int or type(api_token) == str:
            await manager.send_personal_message({"payload": "KILL_CONN", "type": "INVALID_IDENTITY_RESPONSE"}, websocket)
            return await ws_close(websocket, 4004)
        for bot in api_token:
            bid = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1", str(bot))
            if bid is None:
                pass
            else:
                websocket.api_token.append(api_token)
                websocket.bot_id.append(bid["bot_id"])
        if websocket.api_token == [] or websocket.bot_id == []:
            await manager.send_personal_message({"payload": "KILL_CONN", "type": "NO_AUTH"}, websocket)
            return await ws_close(websocket, 4004)
    await manager.send_personal_message({"payload": "STATUS", "type": "READY", "data": [str(bid) for bid in websocket.bot_id]}, websocket)
    try:
        ini_events = {}
        for bot in websocket.bot_id:
            events = await redis_db.hget(str(bot), key = "ws")
            if events is None:
                events = {} # Nothing
            else:
                try:
                    events = orjson.loads(events)
                except Exception as exc:
                    print(exc)
                    events = {}
            ini_events[str(bot)] = events
        await manager.send_personal_message({"payload": "EVENTS", "type": "EVENTS_V1", "data": ini_events}, websocket)
        pubsub = redis_db.pubsub()
        for bot in websocket.bot_id:
            await pubsub.subscribe(str(bot))
        async for msg in pubsub.listen():
            print(msg)
            if msg is None or type(msg.get("data")) != bytes:
                continue
            await manager.send_personal_message({"payload": "EVENTS", "type": "EVENTS_V1", "data": {msg.get("channel").decode("utf-8"): orjson.loads(msg.get("data"))}}, websocket)
    except:
        try:
            await pubsub.unsubscribe()
        except:
            pass
        await manager.disconnect(websocket)

# Chat

@router.websocket("/api/v1/ws/chat")
async def chat_api(websocket: WebSocket):
    await manager_chat.connect(websocket)
    if not websocket.authorized:
        await manager_chat.send_personal_message({"payload": "IDENTITY", "type": "USER|BOT"}, websocket)
        try:
            identity = await websocket.receive_json()
            print("HERE")
            if identity.get("payload") != "IDENTITY_RESPONSE":
                raise TypeError
        except:
            await manager_chat.send_personal_message({"payload": "KILL_CONN", "type": "INVALID_IDENTITY_RESPONSE"}, websocket)
            return await ws_close(websocket, 4004)
        data = identity.get("data")
        if data is None or type(data) != str:
            await manager_chat.send_personal_message({"payload": "KILL_CONN", "type": "NO_AUTH"}, websocket) # Invalid api token provided
            return await ws_close(websocket, 4004)
        match identity.get("type"):
            case "USER":
                acc_type = 0
                sender = await db.fetchval("SELECT user_id FROM users WHERE api_token = $1", identity.get("data"))
            case "BOT":
                acc_type = 1
                sender = await db.fetchval("SELECT bot_id FROM bots WHERE api_token = $1", identity.get("data"))
            case _:
                await manager_chat.send_personal_message({"payload": "KILL_CONN", "type": "NOT_IMPLEMENTED"}, websocket)
                return await ws_close(websocket, 4005) # 4005 = Not Implemented
        if sender is None:
            await manager_chat.send_personal_message({"payload": "KILL_CONN", "type": "NO_AUTH"}, websocket) # Invalid api token provided
            return await ws_close(websocket, 4004)
    websocket.authorized = True
    await manager_chat.send_personal_message({"payload": "CHAT_USER", "type": "CHAT", "data": (await get_any(sender))}, websocket)
    try:
        await redis_db.incrbyfloat(str(sender) + "_cli_count")
        messages = await redis_db.hget("global_chat", key = "message")
        if messages is None:
            messages = b"" # No messages
        await manager_chat.send_personal_message({"payload": "MESSAGE", "type": "BULK", "data": messages.decode("utf-8")}, websocket) # Send all messages in bulk
        pubsub = redis_db.pubsub()
        await pubsub.subscribe("global_chat_channel")
        async for msg in pubsub.listen():
            print("Got msg")
            if type(msg['data']) != bytes:
                continue
            try:
                msg_info = orjson.loads(msg['data'].decode('utf-8'))
            except:
                continue
            await manager_chat.send_personal_message(msg_info, websocket) # Send all messages in bulk
    except Exception as e:
        await redis_db.decrby(str(sender) + "_cli_count")
        print(e)
        await pubsub.unsubscribe()
        await manager_chat.disconnect(websocket)

async def chat_publish_message(msg):
    pass

# End Chat
