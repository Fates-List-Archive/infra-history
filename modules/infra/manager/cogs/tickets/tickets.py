"""Fates List Ticketing System"""

import asyncio
import io
import uuid
from http import HTTPStatus
from typing import Optional, Union

import discord
from core import BotListView, BotState, MenuState, MiniContext, request
from discord import AllowedMentions, Color, Embed, Member, TextChannel, User
from discord.ext import commands

from config import (
    certify_channel,
    ddr_channel,
    general_support_channel,
    reports_channel,
    staff_apps_channel,
    staff_ping_role,
    support_channel,
)
from modules.core.ipc import redis_ipc_new


class TicketMenu(discord.ui.View):
    def __init__(self, bot, public):
        super().__init__(timeout=None)
        self.public = public
        self.state = MenuState.rot
        self.select_menu = _TicketCallback(bot=bot,
                                           placeholder="How can we help?",
                                           options=[])
        self.select_menu.add_option(
            label="General Support",
            value="support",
            description="General support on Fates List",
            emoji="🎫",
        )
        self.select_menu.add_option(
            label="Certification",
            value="certify",
            description="Certification requests",
            emoji="✅",
        )
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
        self.state = MenuState.rot
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        f = getattr(self, self.values[0])
        await self.view.msg.edit(view=self.view
                                 )  # Force reset select menu for user
        return await f(interaction)

    async def support(self, interaction):
        await interaction.response.defer()
        err = await redis_ipc_new(self.bot.redis,
                                  "SUPPORT",
                                  args=[str(interaction.author.id)],
                                  timeout=5)
        if err != b"0":
            if isinstance(err, bytes):
                err = err.decode("utf-8")
            return await interaction.send(
                # f"Please go to <#{general_support_channel}> and make a thread there!\n"
                f"Could not create private thread because: **{err}**",
                ephemeral=True,
            )
        return await interaction.send(
            "Created a private thread for you. Staff will assist you when they can!",
            ephemeral=True,
        )

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

    async def certify(self, interaction):
        res = await request(
            "GET",
            MiniContext(interaction.user, self.bot),
            f"/api/users/{interaction.user.id}",
            staff=False,
        )
        if res[0] == 404:
            return await interaction.response.send_message(
                "You have not even logged in even once on Fates List!",
                ephemeral=True)
        profile = res[1]
        if not profile["approved_bots"]:
            return await interaction.response.send_message(
                "You do not have any approved bots...", ephemeral=True)

        view = BotListView(self.bot, interaction, profile["approved_bots"],
                           None, _CertifySelect)
        return await interaction.response.send_message(
            "Please choose the bot you wish to request certification for",
            view=view,
            ephemeral=True,
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
        self.state = MenuState.rot
        self.bot = bot
        self.app_id = uuid.uuid4()
        self.questions = StaffQuestionList([
            StaffQuestion(
                id="tz",
                question="Please DM me your timezone (the 3 letter code) to start your staff application. **By continuing, you agree that staff applications are public for voting**",
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


class _CertifySelect(discord.ui.Select):
    def __init__(self, bot, inter, action, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.inter = inter
        self.action = action
        self.state = MenuState.rot

    async def callback(self, interaction: discord.Interaction):
        self.disabled = True
        await interaction.response.defer()
        self.view.stop()
        if int(self.values[0]) == -1:
            await interaction.followup.send(
                "Please DM me the bot id you wish to certify", ephemeral=True)

            def id_check(m):
                return (m.content.isdigit()
                        and m.author.id == interaction.user.id
                        and isinstance(m.channel, discord.DMChannel)
                        and len(m.content) in (16, 17, 18, 19, 20))

            try:
                id = await self.bot.wait_for("message",
                                             check=id_check,
                                             timeout=180)
                await id.channel.send(
                    f"Ok, now go back to <#{interaction.channel_id}> to continue certification :)"
                )
            except Exception as exc:
                return await interaction.followup.send(
                    "You took too long to respond!", ephemeral=True)

            id = int(id.content)

        else:
            id = int(self.values[0])

        res = await request(
            "GET",
            MiniContext(interaction.user, self.bot),
            f"/api/bots/{id}?compact=true&no_cache=true",
            staff=False,
        )
        if res[0] != 200:
            return await interaction.followup.send(
                f"Either this bot does not exist or our API is having an issue (got status code {res[0]})",
                ephemeral=True,
            )

        bot = res[1]

        for owner in bot["owners"]:
            if int(owner["user"]["id"]) == interaction.user.id:
                break
        else:
            return await interaction.followup.send(
                f"**You may not request certification for bots you do not own!**",
                ephemeral=True,
            )

        if bot["state"] == BotState.certified:
            return await interaction.followup.send(
                "**This bot is already certified!**", ephemeral=True)

        if bot["state"] != BotState.approved:
            state = BotState(bot["state"])
            return await interaction.followup.send(
                f"**This bot is not eligible for certification as it is currently {state.__doc__} ({state.value})**",
                ephemeral=True,
            )

        if not bot["banner_page"] and not bot["banner_card"]:
            return await interaction.followup.send(
                f"**This bot is not eligible for certification as it is does not have a bot card banner and/or a bot page banner**",
                ephemeral=True,
            )

        if bot["guild_count"] < 100:
            return await interaction.followup.send(
                ("**This bot is not eligible for certification as it is either does not post stats or "
                 f"does not meet even our bare minimum requirement of 100 guilds (in {bot['guild_count']} guilds according to our API)**"
                 ),
                ephemeral=True,
            )

        channel = self.bot.get_channel(certify_channel)
        embed = Embed(title="Certification Request")
        embed.add_field(name="User", value=str(interaction.user))
        embed.add_field(name="User ID", value=str(interaction.user.id))
        embed.add_field(name="Bot Name", value=bot["user"]["username"])
        embed.add_field(name="Description", value=bot["description"])
        embed.add_field(name="Bot ID", value=str(id))
        embed.add_field(name="Guild Count", value=bot["guild_count"])
        embed.add_field(name="Link", value=f"https://fateslist.xyz/{id}")
        embed.add_field(name="Invite Link", value=bot["invite_link"])
        await channel.send(
            f"<@&{staff_ping_role}>",
            embed=embed,
            allowed_mentions=AllowedMentions.all(),
        )

        await interaction.followup.send(
            ("Your certification request has been sent successfully. You will be DM'd by a staff member as soon as they are ready to look at your bot! "
             "Be sure to have your DMs open!"),
            ephemeral=True,
        )


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
