import time
from http import HTTPStatus
from typing import Optional
import asyncpg
import aiohttp

from core import MiniContext, Status, UserState, blstats, profile, InteractionWrapper
from discord import Color, Embed, Member, User
from discord.ext import commands, tasks

from config import (
    main,
    main_botdev_role,
    main_certdev_role,
    staff,
    stats_channel,
    testing,
)


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
            ctx = MiniContext(self.bot.guilds[0].owner, self.bot)
            stats = await blstats(ctx)
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
        _profile = await profile(inter, target)
        if not _profile:
            return
        embed = Embed(title=f"{target}'s Profile",
                      description="Here is your profile")

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
