"""
    Deletes all user data and sets a deleted and banned flag to prevent login. Also removes user from extra owner in all bots, removes user from bot stats and vote timestamps

    Usage:
    Enter util folder using cd util/
    Run python
    
    import deleteuserdata
    deleteuserdata.run(USER_Id)
"""
import asyncpg, asyncio, uvloop, aioredis
import sys
sys.path.append("..")
from config import *

async def _delud(user_id: int):
    db = await asyncpg.create_pool(host="127.0.0.1", port=5432, user=pg_user, password=pg_pwd, database="fateslist")
    await db.execute("DELETE FROM users WHERE user_id = $1", user_id)
    await db.execute("INSERT INTO users (user_id, state) VALUES ($1, 4)", user_id) # INSERT minimal data for banning
    bots = await db.fetch("SELECT DISTINCT bots.bot_id FROM bots INNER JOIN bot_owner ON bot_owner.bot_id = bots.bot_id WHERE bot_owner.owner = $1 AND bot_owner.main = true", user_id)
    for bot in bots:
        for table in "bots", "bot_commands", "bot_owner", "bot_reviews", "bot_stats_votes", "bot_stats_votes_pm", "bot_voters", "bot_api_event", "bot_promotions", "bot_maint":
            await db.execute(f"DELETE FROM {table} WHERE bot_id = $1", bot["bot_id"])
    await db.execute("DELETE FROM bot_owner WHERE owner = $1", user_id)
    await db.execute("DELETE FROM bot_voters WHERE user_id = $1", user_id)

    redis_db = await aioredis.from_url('redis://localhost', db = 1)
    await redis_db.hdel(str(user_id), 'cache')
    await redis_db.close()

# Run the task
def run(user_id):
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    asyncio.get_event_loop().run_until_complete(_delud(user_id))
