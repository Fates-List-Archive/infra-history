from modules.core import *
from ..base import API_VERSION

router = APIRouter(
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Websockets"]
) # No arguments needed for websocket but keep for chat

builtins.manager = ConnectionManager()

@router.websocket("/api/v2/ws/rtstats")
async def websocket_bot_rtstats_v1(websocket: WebSocket):
    logger.debug("Got websocket connection request. Connecting...")
    await manager.connect(websocket)
    if websocket.api_token == [] and not websocket.manager_bot:
        logger.debug("Sending IDENTITY to websocket")
        await manager.send_personal_message(ws_identity_payload(), websocket)
        
        try:
            data = await websocket.receive_json()
            logger.debug("Got response from websocket. Checking response...")
            if (data["m"]["e"] != enums.APIEvents.ws_identity_res 
                or enums.APIEventTypes(data["m"]["t"]) not in [enums.APIEventTypes.auth_token, enums.APIEventTypes.auth_manager_key]):
                return await ws_kill_invalid(manager, websocket)
        except Exception:
            return await ws_kill_invalid(manager, websocket)

        match data["m"]["t"]:
            case enums.APIEventTypes.auth_token:
                try:
                    auth_dict = data["ctx"]["auth"]
                    event_filter = data["ctx"].get("filter")
                except:
                    return await ws_kill_invalid(manager, websocket) 
                if not isinstance(auth_dict, list): 
                    return await ws_kill_invalid(manager, websocket)
                for bot in auth_dict:
                    if not isinstance(bot, dict):
                        continue
                    id = bot.get("id")
                    token = bot.get("token")
                    if not token or not isinstance(token, str):
                        continue
                    if not id or not isinstance(id, str) or not id.isdigit():
                        continue
                    bid = await db.fetchrow("SELECT bot_id FROM bots WHERE api_token = $1 AND bot_id = $2", token, int(id))
                    if bid:
                        rl = await redis_db.get(f"identity-{id}")
                        if not rl:
                            rl = []
                            exp = {"ex": 60*60*24}
                        else:
                            rl = orjson.loads(rl)
                            exp = {"keepttl": True}
                        if len(rl) > 100: 
                            continue
                        elif time.time() - rl[-1] > 5 and time.time() - rl[-1] < 65:
                            continue
                        rl.append(time.time())
                        await redis_db.set(f"identity-{id}", orjson.dumps(rl), **exp)
                        websocket.bots.append(bot)
                if websocket.bots == []:
                    return await ws_kill_no_auth(manager, websocket)
                logger.debug("Authenticated successfully to websocket")
                websocket.authorized = True
                await manager.send_personal_message({
                    "m": {
                        "e": enums.APIEvents.ws_status, 
                        "eid": str(uuid.uuid4()), 
                        "t": enums.APIEventTypes.ws_ready
                    }, 
                    "ctx": {
                        "bots": [{"id": bot['id'], "ws_api": f"/api/bots/{bot['id']}/ws_events"} for bot in websocket.bots]
                    }
                }, websocket)
        
            case enums.APIEventTypes.auth_manager_key:
                try:
                    if secure_strcmp(data["ctx"]["key"], test_server_manager_key):
                        websocket.manager_bot = True
                        event_filter = data["ctx"].get("filter")
                    else:
                        return await ws_kill_no_auth(manager, websocket) 
                except:
                    return await ws_kill_invalid(manager, websocket)
                await manager.send_personal_message({
                    "m": {
                        "e": enums.APIEvents.ws_status, 
                        "eid": str(uuid.uuid4()), 
                        "t": enums.APIEventTypes.ws_ready
                    }, 
                    "ctx": {
                    }
                }, websocket)
    
    try:
        if isinstance(event_filter, int):
            event_filter = [event_filter]
        elif not isinstance(event_filter, list):
            event_filter = None
    
        if not websocket.manager_bot:
            pubsub = redis_db.pubsub()
            for bot in websocket.bots:
                await pubsub.subscribe(f"bot-{bot['id']}")
        
        else:
            pubsub = redis_db.pubsub()
            await pubsub.psubscribe("*")
    
        async for msg in pubsub.listen():
            logger.debug(f"Got message {msg} with manager status of {websocket.manager_bot}")
            if msg is None or type(msg.get("data")) != bytes:
                continue
        
            data = orjson.loads(msg.get("data"))
            event_id = list(data.keys())[0]
            event = data[event_id]
            bot_id = msg.get("channel").decode("utf-8").split("-")[1]
            event["m"]["id"] = bot_id
            
            logger.debug(f"Parsing event {event} with manager status of {websocket.manager_bot}")
            try:
                if not event_filter or event["m"]["e"] in event_filter:
                    flag = True
                else:
                    flag = False
            
            except Exception as exc:
                flag = False
                raise exc
            
            if flag:
                logger.debug("Sending event now...")
                rc = await manager.send_personal_message(event, websocket)
            
                if not websocket.authorized:
                    await ws_close(websocket, 4007) 
    
    except Exception as exc:
        print(exc)
        websocket.authorized = False
    
        try:
            await pubsub.unsubscribe()
        except:
            pass
        
        await ws_close(websocket, 4006)
        raise exc
        await manager.disconnect(websocket)
