from .imports import *

async def bot_auth(bot_id: int, api_token: str):
    return await db.fetchval("SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2", bot_id, str(api_token))

async def user_auth(user_id: int, api_token: str):
    if isinstance(user_id, int):
        pass
    elif user_id.isdigit():
        user_id = int(user_id)
    else:
        return None
    return await db.fetchval("SELECT user_id FROM users WHERE user_id = $1 AND api_token = $2", user_id, str(api_token))

async def bot_auth_check(bot_id: int, Authorization: str = Header("Put Bot Token Here")):
    id = await bot_auth(bot_id, Authorization)
    if id is None:
        raise HTTPException(status_code=401, detail="Invalid Bot Token")

async def user_auth_check(user_id: int, Authorization: str = Header("Put User Token Here")):
    id = await user_auth(user_id, Authorization)
    if id is None:
        raise HTTPException(status_code=401, detail="Invalid User Token")

async def user_bb_auth_check(user_id: int, Authorization: str = Header("Put User Token Or BotBlock(bot_id: int, user_id: Optional[int] = None, Authorization: str = Header("BOT_TOKEN_OR_USER_TOKEN") Key Here")):
    if secure_strcmp(Authorization, bb_key):
        return True
    id = await user_auth(user_id, Authorization)
    if id is None:
        raise HTTPException(status_code=401, detail="Invalid User Token or Botblock Key")

async def bot_user_auth_check(bot_id: int, user_id: Optional[int] = None, Authorization: str = Header("Put Bot Token or User Token here")):
    id = await bot_auth(bot_id, Authorization)
    if id is None and user_id:
        id = await user_auth(user_id, Authorization)
    if id is None and user_id: # Recheck here after checking user token
        raise HTTPException(status_code=401, detail="Invalid Bot Token or User Token")
