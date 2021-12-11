"""Fates List Ticketing System"""

import asyncio
import io
import uuid
from http import HTTPStatus
from typing import Optional, Union

import discord
from core import (
    BotAdminOp,
    BotListView,
    BotState,
    MenuState,
    MiniContext,
    is_staff,
    log,
    request,
)
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
            label="Bot/User Report",
            value="report",
            description="Want to report a misbehaving bot or user?",
            emoji="🔴",
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
        err = await redis_ipc_new(self.bot.redis, "SUPPORT", args=[str(interaction.author.id)])
        if err != b"0":
            return await interaction.send(
                f"Please go to <#{general_support_channel}> and make a thread there!\nCould not create private thread because: {err}",
                ephemeral=True,
            )
        return await interaction.send("Created private thread!", ephemeral=True)

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

    async def report(self, interaction):
        view = _ReportView(interaction, self.bot)
        return await interaction.response.send_message(
            "What would you like to report", view=view, ephemeral=True)


class _ReportView(discord.ui.View):
    def __init__(self, interaction, bot):
        super().__init__()
        self.interaction = interaction
        self.bot = bot
        self.select_menu = _ReportCallback(
            bot=bot, placeholder="What would you like to report?", options=[])
        self.select_menu.add_option(label="Bot", value="bot")
        self.select_menu.add_option(label="User", value="user")
        self.add_item(self.select_menu)


class _ReportCallback(discord.ui.Select):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = MenuState.rot
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        self.view.stop()
        await interaction.response.send_message(
            f"Please DM me the {self.values[0]} ID you wish to report",
            ephemeral=True)

        def id_check(m):
            return (m.content.isdigit() and m.author.id == interaction.user.id
                    and isinstance(m.channel, discord.DMChannel)
                    and len(m.content) in (16, 17, 18, 19, 20))

        try:
            report_id = await self.bot.wait_for("message",
                                                check=id_check,
                                                timeout=180)
        except Exception as exc:
            return await interaction.followup.send(
                "You took too long to respond!", ephemeral=True)

        id = int(report_id.content)

        res = await request(
            "GET",
            MiniContext(interaction.user, self.bot),
            f"/api/users/{id}/obj",
            staff=False,
        )
        if res[0] != 200:
            return await report_id.channel.send(
                f"Either this user does not exist or our API is down (got status code {res[0]})"
            )

        if res[1]["bot"] and self.values[0] == "user":
            return await report_id.channel.send(
                f"This user is not a user but is a bot")

        if not res[1]["bot"] and self.values[0] == "bot":
            return await report_id.channel.send(
                f"This user is not a bot but is a regular user")

        def msg_check(m):
            return m.author.id == interaction.user.id and isinstance(
                m.channel, discord.DMChannel)

        await report_id.channel.send(
            f"Please tell us what this {self.values[0]} has done! Do not send an atttachment or picture, just in words!\n\nProvide message links if you have them!"
        )

        try:
            report_txt = await self.bot.wait_for("message",
                                                 check=msg_check,
                                                 timeout=180)
        except Exception as exc:
            return await interaction.followup.send(
                "You took too long to respond!", ephemeral=True)

        view = _ReportProof(
            interaction,
            self.bot,
            self.values[0],
            report_id.channel,
            id,
            report_txt.content,
        )
        return await report_id.channel.send(
            "Do you have any attachments/extra proof etc. that you are willing to provide?",
            view=view,
        )


class _ReportProof(discord.ui.View):
    def __init__(self, interaction, bot, target, dm, id, report_txt):
        super().__init__()
        self.interaction = interaction
        self.bot = bot
        self.id = id
        self.target = target
        self.report_txt = report_txt
        self.report_id = uuid.uuid4()
        self.dm = dm

    async def _send_report(self, interaction, proof):
        proof = "\n\n".join(proof)
        report = [
            f"Target: {self.target}\n{self.target.title()} ID: {self.id}\nReport ID: {self.report_id}",
            f"Report:\n{self.report_txt}",
            f"Proof/Extra Info:\n{proof}",
        ]
        staff_channel = self.bot.get_channel(reports_channel)
        await staff_channel.send(
            f"<@&{staff_ping_role}>",
            file=discord.File(
                io.BytesIO("\n\n\n".join(report).encode()),
                filename=f"report-{self.report_id}.txt",
            ),
            allowed_mentions=AllowedMentions.all(),
        )
        return await interaction.followup.send(
            "Report successfully sent. Please note that spamming reports may lead to getting banned from Fates List!"
        )

    @discord.ui.button(label="Yes")
    async def proof_recv(self, button, interaction):
        self.stop()

        def msg_check(m):
            return m.author.id == interaction.user.id and isinstance(
                m.channel, discord.DMChannel)

        await interaction.response.send_message(
            "Please post any attachments/screenshots/extra info you are willing to share!"
        )

        try:
            extra = await self.bot.wait_for("message",
                                            check=msg_check,
                                            timeout=180)
        except Exception as exc:
            return await interaction.followup.send(
                "You took too long to respond!")

        extra_info = [extra.content
                      ] + [attachment.url for attachment in extra.attachments]
        return await self._send_report(interaction, extra_info)

    @discord.ui.button(label="No")
    async def no_proof(self, button, interaction):
        self.stop()
        await interaction.response.defer()
        return await self._send_report(
            interaction, ["No extra proof/info willing to be provided"])


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


class _SelectAgeCallback(discord.ui.Select):
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = MenuState.rot
        self.bot = bot
        self.app_id = uuid.uuid4()
        self.questions = {
            "tz":
            "Please DM me your timezone (the 3 letter code) to start your staff application",
            "exp":
            "Do you have experience being a bot reviewer? If so, from where and how long/much experience do you have? How confident are you at handling bots?",
            "lang":
            "How well do you know English? What other languages do you know? How good are you at speaking/talking/listening?",
            "why": "Why are you interested in being staff here at Fates List?",
            "contrib": "What do you think you can contribute to Fates List?",
            "talent":
            "What, in your opinion, are your strengths and weaknesses?",
            "will": "How willing are you to learn new tools and processes?",
        }

        self.answers = {}

    async def callback(self, interaction: discord.Interaction):
        self.disabled = True
        await interaction.response.edit_message(view=self.view)
        self.view.stop()

        if self.values[0] == "not_eligible":
            return await interaction.followup.send(
                "You are unfortunately not eligible to apply for staff!",
                ephemeral=True)

        await interaction.followup.send(self.questions["tz"], ephemeral=True)

        def app_check(m):
            return m.author.id == interaction.user.id and isinstance(
                m.channel, discord.DMChannel)

        def app_ext_check(m):
            return app_check(m) and len(m.content) > 30

        def tz_check(m):
            return app_check(m) and len(m.content) == 3 and m.content.isalpha()

        try:
            tz = await self.bot.wait_for("message",
                                         check=tz_check,
                                         timeout=180)
        except Exception as exc:
            return await interaction.followup.send(
                "You took too long to respond!", ephemeral=True)

        self.answers["tz"] = tz.content.upper()

        for q in self.questions.keys():
            if q == "tz":
                continue

            await tz.channel.send(
                f"**{self.questions[q]}**\n\nUse at least 30 characters!")

            try:
                ans = await self.bot.wait_for("message",
                                              check=app_ext_check,
                                              timeout=180)
            except Exception as exc:
                return await interaction.followup.send(
                    "You took too long to respond!", ephemeral=True)

            self.answers[q] = ans.content

        data = [
            f"Username: {interaction.user}\nUser ID: {interaction.user.id}\nAge Range: {self.values[0]}\nApplication ID: {self.app_id}"
        ]
        for q in self.questions.keys():
            data.append(
                f"{q}\n\nQuestion: {self.questions[q]}\n\nAnswer: {self.answers[q]}"
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
            f"/api/bots/{id}?compact=false",
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

        elif bot["state"] != BotState.approved:
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
