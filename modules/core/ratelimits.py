from .imports import *

def ip_check(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        logger.trace(f"Forwarded IPs are {forwarded}")
        return forwarded.split(",")[0]
    return request.client.host

async def rl_key_func(request: Request) -> str:
    if secure_strcmp(request.headers.get("FatesList-RateLimitBypass"), ratelimit_bypass_key): # Check ratelimit key
        return None
    if ("Authorization" in request.headers or "authorization" in request.headers) and str(request.url.path).startswith("/api/"):
        try: # Check for auth header
            r = request.headers["Authorization"]
        except KeyError:
            r = request.headers["authorization"]
        check = await db.fetchrow("SELECT bot_id, state FROM bots WHERE api_token = $1", r) # Check api token
        if check is None:
            # Check user token too
            check_user = await db.fetchval("SELECT user_id FROM users WHERE api_token = $1", r) # Check api token
            if check_user is None:
                return ip_check(request) # Invalid api token, fallback to ip
            else:
                return str(check_user)
        if check["state"] == enums.BotState.certified:
            return None
        return str(check["bot_id"]) # Otherwise, ratelimit using bot id
    else:
        return ip_check(request) # Fallback to ip
