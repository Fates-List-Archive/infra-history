from .base import DiscordUser
from .bot import Bot
from .badge import Badge
from modules.core.cache import get_user
from modules.core.helpers import redis_ipc_new
from modules.models import enums   
import orjson

class User(DiscordUser):
    """A user on Fates List"""
    async def fetch(self):
        """Fetch a user object from our cache"""
        return await get_user(self.id)

    async def profile(self):
        """Gets a users profile"""
        user = await self.db.fetchrow(
            "SELECT bot_logs, badges, state, description, css, js_allowed FROM users WHERE user_id = $1", 
            self.id
        )
        
        if user is None:
            return None
        
        user_obj = await self.fetch()
        if user_obj is None:
            return None
        
        user = dict(user)

        user["bot_logs"] = orjson.loads(user["bot_logs"])
    
        # TODO: This whole section
        _bots = await self.db.fetch(
            """SELECT bots.description, bots.prefix, bots.banner_card AS banner, bots.state, bots.votes, 
            bots.guild_count, bots.bot_id, bots.nsfw FROM bots 
            INNER JOIN bot_owner ON bot_owner.bot_id = bots.bot_id 
            WHERE bot_owner.owner = $1""",
            self.id
        )
        
        bots = []
        for bot in _bots:
            bot_obj = Bot(id = bot["bot_id"], db = self.db)
            bots.append(dict(bot) | {"invite": await bot_obj.invite_url(), "user": await bot_obj.fetch()})
        
        approved_bots = [obj for obj in bots if obj["state"] in (enums.BotState.approved, enums.BotState.certified)]
        certified_bots = [obj for obj in bots if obj["state"] == enums.BotState.certified]
    
        user["bot_developer"] = approved_bots != []
        user["certified_developer"] = certified_bots != []                      
                         
        on_server = await redis_ipc_new(redis_db, "ROLES", args=[str(self.id)])
        if on_server == b"-1" or not on_server:
            on_server = b""
        user["badges"] = await Badge.from_user(self.id, on_server.decode("utf-8").split(" "), user["badges"], user["bot_developer"], user["certified_developer"])
                         
        return {
            "bots": bots, 
            "approved_bots": approved_bots, 
            "certified_bots": certified_bots, 
            "profile": user,
            "dup": True,
            "user": user_obj
        }
