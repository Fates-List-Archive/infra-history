import time
import asyncpg
import aiohttp
import asyncio
import datetime
from modules.models.enums import UserState, Status
from fateslist import UserClient, APIResponse
from discord import Color, Embed, User
from discord.ext import commands, tasks

from config import (
    main,
    staff,
    stats_channel
)

# TODO: Port this to fateslist.py as well
# usage: (_d, _h, _m, _s, _mils, _mics) = tdTuple(td)
def extract_time(td: datetime.timedelta) -> tuple:
    def _t(t, n):
        if t < n:
            return (t, 0)
        v = t // n
        return (t - (v * n), v)

    (s, h) = _t(td.seconds, 3600)
    (s, m) = _t(s, 60)
    return (td.days, h, m, s)

async def blstats():
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f"https://api.fateslist.xyz/api/blstats?workers=true") as res:
                status = res.status
                res = await res.json()
                res = [status, res]
    except Exception as exc:
        res = [
            502,
            {
                "uptime": 0,
                "pid": 0,
                "up": False,
                "server_uptime": 0,
                "bot_count": "Unknown",
                "bot_count_total": "Unknown",
                "error": f"{type(exc).__name__}: {exc} - Servers likely down",
                "workers": [0],
            },
        ]
    embed = Embed(title="Bot List Stats", description="Fates List Stats")
    uptime_tuple = extract_time(datetime.timedelta(seconds=res[1]["uptime"]))
    # ttvr = Time Till Votes Reset
    ttvr_tuple = extract_time(
        (datetime.datetime.now().replace(day=1, second=0, minute=0, hour=0) +
         datetime.timedelta(days=32)).replace(day=1) - datetime.datetime.now())
    uptime = "{} days, {} hours, {} minutes, {} seconds".format(*uptime_tuple)
    ttvr = "{} days, {} hours, {} minutes, {} seconds".format(*ttvr_tuple)
    embed.add_field(name="Uptime", value=uptime)
    embed.add_field(name="Time Till Votes Reset", value=ttvr)
    embed.add_field(name="Worker PID", value=str(res[1]["pid"]))
    embed.add_field(name="Worker Number",
                    value=res[1]["workers"].index(res[1]["pid"]) + 1)
    embed.add_field(
        name="Workers",
        value=f"{', '.join([str(w) for w in res[1]['workers']])} ({len(res[1]['workers'])} workers)",
    )
    embed.add_field(name="UP?", value=str(res[1]["up"]))
    embed.add_field(name="Server Uptime", value=str(res[1]["server_uptime"]))
    embed.add_field(name="Bot Count", value=str(res[1]["bot_count"]))
    embed.add_field(name="Bot Count (Total)",
                    value=str(res[1]["bot_count_total"]))
    embed.add_field(
        name="Errors",
        value=res[1]["error"]
        if res[1].get("error") else "No errors fetching stats from API",
    )
    return embed

class InteractionWrapper:
    def __init__(self, interaction, ephemeral: bool = False):
        self.interaction = interaction
        asyncio.create_task(self.auto_defer(ephemeral))

    async def auto_defer(self, ephemeral: bool):
        start_time = time.time()
        while time.time(
        ) - start_time < 15 and not self.interaction.response.is_done():
            await asyncio.sleep(0)
        
        if not self.interaction.response.is_done():
            await self.interaction.response.defer(ephemeral=ephemeral)

    async def send(self, *args, **kwargs):
        return await self.interaction.send(*args, **kwargs)

class Users(commands.Cog):
    """Commands made specifically for users to use"""

    def __init__(self, bot):
        self.bot = bot
        self.msg = None
        self.statloop.start()

    @commands.slash_command(
        name="catid",
        description="Get the category ID of a channel",
        guild_ids=[main, staff],
    )
    async def catid(self, inter):
        return await self._catid(inter)
    
    @commands.slash_command(
        name="vote",
        description="Vote for a bot",
    )
    async def _vote_slash(self, inter, bot: User):
        InteractionWrapper(inter) # This also autodefers
        await self._vote(inter, bot)

    @commands.command(
        name="vote",
        description="Vote for a bot"
    )
    async def _vote_normal(self, ctx, bot: User):
        await self._vote(ctx, bot)
    
    async def _vote(self, inter, bot: User):
        if not bot.bot:
            return await inter.send(
                "You can only vote for bots at this time!"
            )
        db: asyncpg.Connection = await asyncpg.connect()
        user_token = await db.fetchval(
            "SELECT api_token from users WHERE user_id = $1",
            inter.author.id
        )
        await db.close()
        async with aiohttp.ClientSession() as sess:
            async with sess.patch(
                f"https://api.fateslist.xyz/api/dragon/bots/{bot.id}/votes",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": user_token,
                    "Mistystar": "1"
                },
                json={"user_id": str(inter.author.id), "test": False}
            ) as res:
                if res.status >= 400:
                    json = await res.json()
                    return await inter.send(f'{json["reason"]}\n**Status Code:** {res.status}')
                return await inter.send("Successfully voted for this bot!")

    @commands.slash_command(name="chanid",
                            description="Get channel id",
                            guild_ids=[main, staff])
    async def chanid(self, inter):
        return await inter.send(str(inter.channel.id))

    @commands.slash_command(name="flstats",
                            description="Show Fates List Stats",
                            guild_ids=[staff])
    async def stats(self, inter):
        return await inter.send(embed=await blstats(inter))

    @commands.slash_command(
        name="flprofile",
        description="Get your own or another users profile",
    )
    async def flprofile(self, inter, user: User = None):
        return await self._profile(inter, user)

    @tasks.loop(minutes=5)
    async def statloop(self):
        try:
            stats = await blstats()
            if not self.msg:
                channel = self.bot.get_channel(stats_channel)
                await channel.purge(
                    limit=100, check=lambda m: m.author.id != m.guild.owner_id
                )  # Delete old messages there
                self.msg = await channel.send(embed=stats)
                await self.msg.pin(reason="Stat Message Pin")
                await channel.purge(
                    limit=1)  # Remove Fates List Manager has pinned...
            else:
                await self.msg.edit(embed=stats)
        except Exception as exc:
            print(f"{type(exc).__name__}: {exc}", flush=True)

    def cog_unload(self):
        self.statloop.cancel()

    @staticmethod
    async def _catid(inter):
        if inter.channel.category:
            return await inter.send(str(inter.channel.category.id))
        return await inter.send("No category attached to this channel")

    @staticmethod
    async def _profile(inter, user=None):
        """Gets a users profile (Not yet done)"""
        target = user if user else inter.author
        uc = UserClient(target.id)
        _profile = await uc.get_user()
        if isinstance(_profile, APIResponse):
            return
        embed = Embed(title=f"{target}'s Profile",
                      description="Here is your profile")

        _profile = _profile.dict()

        # Base fields
        embed.add_field(name="User ID", value=_profile["user"]["id"])
        embed.add_field(name="Username", value=_profile["user"]["username"])
        embed.add_field(name="Discriminator/Tag",
                        value=_profile["user"]["disc"])
        embed.add_field(name="Avatar", value=_profile["user"]["avatar"])
        embed.add_field(name="Description",
                        value=_profile["profile"]["description"])
        embed.add_field(
            name="Status",
            value=f"{_profile['user']['status']} ({Status(_profile['user']['status']).__doc__})",
        )
        embed.add_field(
            name="State",
            value=f"{_profile['profile']['state']} ({UserState(_profile['profile']['state']).__doc__})",
        )
        embed.add_field(
            name="User CSS",
            value=_profile["profile"]["user_css"]
            if _profile["profile"]["user_css"] else "No custom user CSS set",
        )

        await inter.send(embed=embed)
