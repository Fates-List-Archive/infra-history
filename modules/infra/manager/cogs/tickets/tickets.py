"""Fates List Ticketing System"""

import asyncio
import io
import uuid
from http import HTTPStatus
from typing import Optional, Union

import discord
from fateslist import BotClient, UserClient, APIResponse
from modules.models.enums import BotState
from discord import AllowedMentions, Color, Embed, Member, TextChannel, User
from discord.ext import commands

from config import (
    ddr_channel,
    general_support_channel,
    reports_channel,
    staff_apps_channel,
    staff_ping_role,
    support_channel,
)
from modules.core.ipc import redis_ipc_new

class BotListView(discord.ui.View):
    def __init__(self, bot, inter, bots, action, select_menu):
        super().__init__()
        self.bots = bots
        self.select_menu = select_menu(
            bot=bot,
            inter=inter,
            action=action,
            placeholder="Please choose the bot",
            options=[],
        )
        options = 0
        for bot in self.bots:
            username = bot["user"]["username"][:25]
            description = bot["description"][:50]

            self.select_menu.add_option(label=username,
                                        description=description,
                                        value=bot["user"]["id"])
            options += 1

            if options == 24:
                break

        self.select_menu.add_option(label="Not listed", value="-1")
        self.add_item(self.select_menu)

class TicketMenu(discord.ui.View):
    def __init__(self, bot, public):
        super().__init__(timeout=None)
        self.public = public
        self.select_menu = _TicketCallback(bot=bot,
                                           placeholder="How can we help?",
                                           options=[])
        # TODO: Add general support when we get the boosts
        self.select_menu.add_option(
            label="Staff Application",
            value="staff_app",
            description="Think you got what it takes to be staff on Fates List?",
            emoji="🛠️",
        )
        self.select_menu.add_option(
            label="Data Deletion Request",
            value="ddr",
            description="This will wipe all data other than when you last voted. May take up to 24 hours",
            emoji="🖨️",
        )

        self.add_item(self.select_menu)


class _TicketCallback(discord.ui.Select):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        f = getattr(self, self.values[0])
        await self.view.msg.edit(view=self.view
                                 )  # Force reset select menu for user
        return await f(interaction)

    async def ddr(self, interaction):
        view = _DDRView(interaction, bot=self.bot)
        await interaction.response.send_message(
            ("Are you sure you wish to request a Data Deletion Request. "
             "All of your bots, profile info and any perks you may have will be wiped from your account! "
             "Your vote epoch (when you last voted) will stay as it is temporary (expires after 8 hours) and is needed for anti-vote "
             "abuse (to prevent vote spam and vote scams etc.)"),
            ephemeral=True,
            view=view,
        )

    async def staff_app(self, interaction):
        view = _StaffAgeView(interaction, self.bot)
        return await interaction.response.send_message(
            "Please select your age. Please do not lie as we can and *will* investigate!",
            view=view,
            ephemeral=True,
        )

class _StaffAgeView(discord.ui.View):
    def __init__(self, interaction, bot):
        super().__init__()
        self.interaction = interaction
        self.bot = bot
        self.select_menu = _SelectAgeCallback(
            bot=bot, placeholder="Select your age range", options=[])
        self.select_menu.add_option(
            label="<=14",
            value="not_eligible",
            description="Less than or equal to 14 years old",
        )  # Not eligible
        self.select_menu.add_option(label="15-18",
                                    value="14-18",
                                    description="15 through 18 years old")
        self.select_menu.add_option(label="18+",
                                    value="adult (18+)",
                                    description="18+ years old")
        self.add_item(self.select_menu)

cancel_list = ["cancel", "quit"]

class StaffQuestion():
    def __init__(self, id: str, question: str, check, parser = None, minlength: int = 30, maxlength = 2000):
        self.id = id
        self.question = question
        self.check = check # Function
        self.parser = parser if parser else lambda m: m.content
        self.minlength = minlength
        self.maxlength = maxlength
        self.answer = None
    
    def q_check(self, m):
        if m.content.lower() in cancel_list:
            return True
        return self.check(m) and len(m.content) >= self.minlength and (not self.maxlength or len(m.content) <= self.maxlength)

class StaffQuestionList():
    def __init__(self, items):
        self.items = items
    
    def get(self, id) -> StaffQuestion:
        for item in self.items:
            if item.id == id:
                return item

class _SelectAgeCallback(discord.ui.Select):
    def app_check(self, m):
        return m.author.id == self.interaction.user.id and isinstance(
            m.channel, discord.DMChannel)

    def app_ext_check(self, m):
        return self.app_check(m)

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.app_id = uuid.uuid4()
        self.questions = StaffQuestionList([
            StaffQuestion(
                id="tz",
                question="Please DM me your timezone (the 3 letter code) to start your staff application. **By continuing, you agree that staff applications could be made public**",
                check=lambda m: self.app_check(m) and m.content.isalpha(),
                parser=lambda m: m.content.upper(),
                minlength=3,
                maxlength=3
            ),
            StaffQuestion(
                id="exp",
                question="Do you have experience being a bot reviewer? If so, from where and how long/much experience do you have? How confident are you at handling bots?",
                check=lambda m: self.app_ext_check(m)
            ),
            StaffQuestion(
                id="lang",
                question="How well do you know English? What other languages do you know? How good are you at speaking/talking/listening?",
                check=lambda m: self.app_ext_check(m)
            ),
            StaffQuestion(
                id="why",
                question="Why are you interested in being staff here at Fates List?",
                check=lambda m: self.app_ext_check(m)
            ),
            StaffQuestion(
                id="contrib",
                question="What do you think you can contribute to Fates List?",
                check=lambda m: self.app_ext_check(m)
            ),
            StaffQuestion(
                id="talent",
                question="What, in your opinion, are your strengths and weaknesses?",
                check=lambda m: self.app_ext_check(m)
            ),
            StaffQuestion(
                id="will",
                question="How willing are you to learn new tools and processes?",
                check=lambda m: self.app_ext_check(m)
            ),
            StaffQuestion(
                id="warn",
                question="Do you understand that being staff here is a privilege and that you may demoted without warning based on your performance.",
                check=lambda m: self.app_ext_check(m),
                minlength=10,
                maxlength=30
            ),
        ])

    async def callback(self, interaction: discord.Interaction):
        self.disabled = True
        self.interaction = interaction
        await interaction.response.edit_message(view=self.view)
        self.view.stop()

        if self.values[0] == "not_eligible":
            return await interaction.followup.send(
                "You are unfortunately not eligible to apply for staff!",
                ephemeral=True)

        await interaction.followup.send(self.questions.get("tz").question, ephemeral=True)

        try:
            tz = await self.bot.wait_for("message",
                                         check=self.questions.get("tz").q_check,
                                         timeout=180)
        except Exception as exc:
            return await interaction.followup.send(
                f"You took too long to respond! {exc}", ephemeral=True)

        self.questions.get("tz").answer = self.questions.get("tz").parser(tz)

        for q in self.questions.items:
            if q.id == "tz":
                continue
        
            await tz.channel.send(
                f"**{q.question}**\n\nUse at least {q.minlength} characters and at most {q.maxlength} characters!")

            try:
                ans = await self.bot.wait_for("message",
                                              check=q.q_check,
                                              timeout=180)
            except Exception as exc:
                return await interaction.followup.send(
                    "You took too long to respond!", ephemeral=True)

            if ans.content.lower() in cancel_list:
                return await ans.channel.send("Cancelled!")

            q.answer = q.parser(ans)

        data = [
            f"Username: {interaction.user}\nUser ID: {interaction.user.id}\nAge Range: {self.values[0]}\nApplication ID: {self.app_id}"
        ]
        for q in self.questions.items:
            data.append(
                f"{q.id}\n\nQuestion: {q.question}\n\nAnswer: {q.answer}"
            )

        staff_channel = self.bot.get_channel(staff_apps_channel)
        await staff_channel.send(
            f"<@&{staff_ping_role}>",
            file=discord.File(
                io.BytesIO("\n\n\n".join(data).encode()),
                filename=f"staffapp-{self.app_id}.txt",
            ),
            allowed_mentions=AllowedMentions.all(),
        )
        await tz.channel.send((
            "Your staff application has been sent and you will be DM'd by a staff member whether you have "
            "been accepted or denied or if we need more information.\n\nFeel free to DM **one** *Head Admin* "
            "if you wish to check on the status of your application or if you have any concerns! **Do not "
            "resend a new application or make a support ticket for this**\n\n\nThank you\nThe Fates List Staff Team"
        ))


class _DDRView(discord.ui.View):
    """Data Deletion Request Confirm View"""

    def __init__(self, interaction, bot):
        super().__init__()
        self.interaction = interaction
        self.bot = bot

    async def disable(self, interaction):
        for button in self.children:
            button.disabled = True
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Yes")
    async def send_ddr(self, button, interaction):
        await self.disable(interaction)
        await interaction.followup.send(
            "Please wait while we send your data deletion request...",
            ephemeral=True)
        channel = self.bot.get_channel(ddr_channel)
        embed = Embed(title="Data Deletion Request")
        embed.add_field(name="User", value=str(interaction.user))
        embed.add_field(name="User ID", value=str(interaction.user.id))
        await channel.send(interaction.guild.owner.mention, embed=embed)
        await interaction.followup.send(
            content="Sent! Your data will be deleted within 24 hours!",
            ephemeral=True)

    @discord.ui.button(label="No")
    async def cancel_ddr(self, button, interaction):
        await self.disable(interaction)
        self.stop()
        await interaction.edit_original_message(content="Cancelled!",
                                                view=None)

class Tickets(commands.Cog):
    """Commands to handle ticketing"""

    def __init__(self, bot):
        self.bot = bot
        self.msg = []
        asyncio.create_task(self._cog_load())

    async def _cog_load(self):
        channel = self.bot.get_channel(support_channel)
        return await self._ticket(channel)

    async def _ticket(self, channel):
        try:
            await channel.purge(
                limit=100,
                check=lambda m:
                (not m.pinned or m.author.id == self.bot.user.id),
            )
        except Exception as exc:
            print(exc, " ...retrying")
            return await self._ticket(channel)
        view = TicketMenu(bot=self.bot, public=True)
        embed = Embed(
            title="Fates List Support",
            description="Hey there 👋! Thank you for contacting Fates List Support. How can we help you?",
        )
        msg = await channel.send(embed=embed, view=view)
        view.msg = msg
        self.msg.append(msg)
        await msg.pin(reason="Support system")
        await channel.purge(limit=1)

    def cog_unload(self):
        try:
            for msg in self.msg:
                asyncio.create_task(msg.delete())
        except Exception as exc:
            print(exc)
        super().cog_unload()
