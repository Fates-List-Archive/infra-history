from .imports import *


def ip_check(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        logger.trace(f"Forwarded IPs are {forwarded}")
        return forwarded.split(",")[0]
    return request.client.host

async def rl_key_func(request: Request) -> str:
    db = request.app.state.worker_session.postgres

    if secure_strcmp(str(request.headers.get("FatesList-RateLimitBypass")), request.app.state.rl_key): # Check ratelimit key
        return None
    
    if ip_check(request) == "127.0.0.1":
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
            return str(check_user)
        if check["state"] == enums.BotState.certified:
            return None
        return str(check["bot_id"]) # Otherwise, ratelimit using bot id
    return ip_check(request) # Fallback to ip
