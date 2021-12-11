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
        self.whitelist = {}  # Staff Server Bot Protection

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

    @dislash.slash_command(
        name="allowbot",
        description="Allows a bot temporarily to the staff server",
        guild_ids=[staff],
    )
    async def allowbot(self, inter, bot: disnake.User):
        """Shhhhh.... secret command to allow adding a bot to the staff server"""
        staff = await is_staff(inter, inter.author.id, 4)
        if not staff[0]:
            return await inter.send(
                "You cannot temporarily whitelist this member as you are not an admin"
            )
        self.whitelist[bot.id] = True
        await inter.send("Temporarily whitelisted for one minute")
        await asyncio.sleep(60)
        try:
            del self.whitelist[bot.id]
        except:
            pass
        try:
            await inter.send("Unwhitelisted bot again")
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_message(self, message):
        # Anti log spam
        if not message.guild:
            return
        if (message.author.id != message.guild.me.id
                and int(message.channel.id) == log_channel):
            await message.delete()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            if member.guild.id == main:
                await member.add_roles(member.guild.get_role(main_bots_role))
                await log(
                    MiniContext(member, self.bot),
                    f"Bot **{member.name}#{member.discriminator}** has joined the main server, hopefully after being properly tested...",
                )
            elif member.guild.id == testing:
                await member.add_roles(member.guild.get_role(test_bots_role))
                await log(
                    MiniContext(member, self.bot),
                    f"Bot **{member.name}#{member.discriminator}** has joined the testing server, good luck...",
                )
            elif not self.whitelist.get(member.id) and member.guild.id == staff:
                await member.kick(reason="Unauthorized Bot")
            else:
                del self.whitelist[member.id]
        else:
            if member.guild.id == testing:
                staff_check = await is_staff(MiniContext(member, self.bot), member.id, 2)
                if staff_check[0]:
                    await member.add_roles(
                        member.guild.get_role(test_staff_role))
