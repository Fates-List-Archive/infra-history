from fastapi import Security
from fastapi.security.api_key import (APIKey, APIKeyCookie, APIKeyHeader,
                                      APIKeyQuery)

from .imports import *

bot_auth_header = APIKeyHeader(name="Authorization", description="These endpoints require a bot token. You can get this from Bot Settings. Make sure to keep this safe and in a .gitignore/.env.\n\nA prefix of `Bot` before the bot token such as `Bot abcdef` is supported and can be used to avoid ambiguity but is not required. The default auth scheme if no prefix is given depends on the endpoint: Endpoints which have only one auth scheme will use that auth scheme while endpoints with multiple will always use `Bot` for backward compatibility", scheme_name="Bot")

user_auth_header = APIKeyHeader(name="Authorization", description="These endpoints require a user token. You can get this from your profile under the User Token section. If you are using this for voting, make sure to allow users to opt out!\n\nA prefix of `User` before the user token such as `User abcdef` is supported and can be used to avoid ambiguity but is not required outside of endpoints that have both a user and a bot authentication option such as Get Votes. In such endpoints, the default will always be a bot auth unless you prefix the token with `User`", scheme_name="User")

server_auth_header = APIKeyHeader(name="Authorization", description="These endpoints require a server token which you can get using /get API Token in your server. Same warnings and information from the other authentication types apply here. A prefix of ``Server`` before the server token is supported and can be used to avoid ambiguity but is not required.", scheme_name="Server")

async def _bot_auth(bot_id: int, api_token: str):
    if isinstance(bot_id, int):
        pass
    elif bot_id.isdigit():
        bot_id = int(bot_id)
    else:
        return None
    if api_token.startswith("Bot "):
        api_token = api_token.replace("Bot ", "", 1)
    return await db.fetchval("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(api_token))

async def _server_auth(server_id: int, api_token: str):
    if isinstance(server_id, int):
        pass
    elif server_id.isdigit():
        server_id = int(server_id)
    else:
        return None
    if api_token.startswith("Server "):
        api_token = api_token.replace("Server ", "", 1)
    return await db.fetchval("SELECT guild_id FROM servers WHERE guild_id = $1 AND api_token = $2", server_id, str(api_token))

async def _user_auth(user_id: int, api_token: str):
    if isinstance(user_id, int):
        pass
    elif user_id.isdigit():
        user_id = int(user_id)
    else:
        return None
    if api_token.startswith("User "):
        api_token = api_token.replace("User ", "", 1)
    user = await db.fetchrow("SELECT user_id, state FROM users WHERE user_id = $1 AND api_token = $2", user_id, str(api_token))
    if not user:
        return
    if user["state"] in (enums.UserState.api_ban, enums.UserState.global_ban):
        raise HTTPException(status_code=400, detail="This user has been banned from using the Fates List API")
    return user["user_id"]

async def server_auth_check(guild_id: int, server_auth: str = Security(server_auth_header)):
    if server_auth.startswith("Server "):
        server_auth = server_auth.replace("Server ", "")
    id = await _server_auth(guild_id, server_auth)
    if id is None:
        raise HTTPException(status_code=401, detail="Invalid Server Token")

async def bot_auth_check(bot_id: int, bot_auth: str = Security(bot_auth_header)):
    if bot_auth.startswith("Bot "):
        bot_auth = bot_auth.replace("Bot ", "", 1)
    id = await _bot_auth(bot_id, bot_auth)
    if id is None:
        raise HTTPException(status_code=401, detail="Invalid Bot Token")

async def user_auth_check(user_id: int, user_auth: str = Security(user_auth_header)):
    if user_auth.startswith("User "):
        user_auth = user_auth.replace("User ", "", 1)
    id = await _user_auth(user_id, user_auth)
    if id is None:
        raise HTTPException(status_code=401, detail=f"Invalid User Token")

async def bot_user_auth_check(bot_id: int, user_id: Optional[int] = None, bot_auth: str = Security(bot_auth_header), user_auth: str = Security(user_auth_header)):
    if user_auth.startswith("User "):
        scheme = "User"
        id = await _user_auth(user_id, user_auth)
    else:
        scheme = "Bot"
        id = await _bot_auth(bot_id, bot_auth)
    
    if not id:
        raise HTTPException(status_code=401, detail=f"Invalid {scheme} Token")

# All bot_server auth endpoints must use target_id and probably uses target_type
async def bot_server_auth_check(target_id: int, target_type: enums.ReviewType, bot_auth: str = Security(bot_auth_header), user_auth: str = Security(server_auth_header)):
    if target_type == enums.ReviewType.server:
        if server_auth.startswith("Bot "):
            raise HTTPException(status_code=401, detail="Invalid token type. Did you use the correct target_type")
        scheme = "Server"
        id = await _server_auth(target_id, server_auth)
    else:
        if bot_auth.startswith("Server "):
            raise HTTPException(status_code=401, detail="Invalid token type. Did you use the correct target_type")
        scheme = "Bot"
        id = await _bot_auth(target_id, bot_auth)

    if not id:
        raise HTTPException(status_code=401, detail=f"Invalid {scheme} Token")
