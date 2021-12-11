import asyncio
import enum
from http import HTTPStatus
from typing import Optional, Union

import discord
from core import BotAdminOp, MiniContext, UserState, is_staff, log
from discord import Color, Embed, Member, TextChannel, User
from discord.ext import commands
from loguru import logger

from config import (
    log_channel,
    main,
    main_bots_role,
    staff,
    staff_roles,
    test_bots_role,
    test_staff_role,
    testing,
)

# For now
disnake = discord
dislash = commands

class Staff(commands.Cog):
    """Commands to handle the staff server"""

    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        description="Bans a user from the list/Sets user state",
        guild_ids=[staff])
    async def userstate(self, inter, user: disnake.User, state: UserState,
                        reason: str):
        staff = await is_staff(inter, inter.author.id, 5)
        if not staff[0]:
            return await inter.send("You are not a Head Admin+!")
        await self.bot.postgres.execute(
            "UPDATE users SET state = $1 WHERE user_id = $2", state.value,
            user.id)
        return await inter.send(f"Set state of {user} successfully to {state}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == testing:
            staff_check = await is_staff(MiniContext(member, self.bot), member.id, 2)
            if staff_check[0]:
                await member.add_roles(
                    member.guild.get_role(test_staff_role))
