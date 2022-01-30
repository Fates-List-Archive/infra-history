from discord.ext import commands
from discord import Embed, Color
import discord
import asyncio
from fateslist import UserClient, APIResponse
from config import ilovepings_role, addbotping_role, newsping_role, role_channel, main_botdev_role, main_certdev_role, bronze_user_role, giveaway_role

class RoleMenu(discord.ui.View):
    def __init__(self, bot, public, roles):
        super().__init__(timeout=None)
        self.public = public
        self.select_menu = _RoleCallback(bot=bot, placeholder="Choose your roles!", options=[], allowed_roles=roles, max_values=len(roles))
        self.select_menu.add_option(
            label="I Love Pings", 
            value="ilovepings", 
            description="Choose this role if you are OK with being pinged for everything we do!", 
            emoji="🏓"
        )
        self.select_menu.add_option(
            label="News Ping", 
            value="newsping", 
            description="Choose this role if you want to be pinged for any announcements we may make",
            emoji="🐱"
        )
        self.select_menu.add_option(
            label="Add Bot Ping", 
            value="addbotping", 
            description="Choose this role if you want to be pinged for any new bot added. Required by all bot reviewers", 
            emoji="🤙"
        )
        self.select_menu.add_option(
            label="Giveaway/Events Ping",
            value="giveaway",
            description="Get notified when Fates List does **giveaways and events**!",
            emoji="🎉"
        )
        self.add_item(self.select_menu)
        
        
class _RoleCallback(discord.ui.Select):
    def __init__(self, bot, allowed_roles, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.allowed_roles = allowed_roles
     
    async def callback(self, interaction: discord.Interaction):
        await self.view.msg.edit(view=self.view) # Force reset select menu for user
        roles_give = []
        roles_take = []
        role_ids = [role.id for role in interaction.user.roles]
        for role in self.values:
            role_id = self.allowed_roles.get(role)
            if not role_id:
                return await interaction.response.send_message(f"{role} does not exist as a key! Please contact Rootspring#6701 for help!", ephemeral=True)
            _role = interaction.guild.get_role(role_id)
            if not _role:
                continue
            if _role.id in role_ids:
                roles_take.append(_role)
            else:
                roles_give.append(_role)
            
        await interaction.user.add_roles(*roles_give)
        await interaction.user.remove_roles(*roles_take)
        roles_give_formatted = " | ".join([role.mention for role in roles_give])
        roles_take_formatted = " | ".join([role.mention for role in roles_take])
        return await interaction.response.send_message(f"Roles Given: {roles_give_formatted}\nRoles Taken: {roles_take_formatted}", ephemeral=True)

    
class _GetRolesView(discord.ui.View):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Get Old Roles")
    async def _getroles(self, button, inter):
        target = inter.user
        uc = UserClient(target.id)
        _profile = await uc.get_user()
        if isinstance(_profile, APIResponse):
            embed = Embed(title = "No Profile Found", description = "You have not even logged in even once on Fates List!", color = Color.red())
            return await inter.response.send_message(embed=embed, ephemeral=True)
        
        embed = Embed(title = "Roles Given", description = "These are the roles you have got on Fates List", color = Color.blue())
    
        success, failed = 0, 0
        keys = (("bot_developer", main_botdev_role, "You are not a bot developer"), ("certified_developer", main_certdev_role, "You do not have any certified bots"))  # List of special roles
        for key in keys:
            role = key[0].replace('_', ' ').title()
            if not _profile.profile[key[0]]:
                embed.add_field(name = role, value = f":x: Not going to give you the {role} role because: *{key[2]}*")
                failed += 1
                continue
            await target.add_roles(inter.guild.get_role(key[1]))
            embed.add_field(name = role, value = f":white_check_mark: Gave you the {role} role")
            success += 1
        
        embed.add_field(name = "Success", value = str(success))
        embed.add_field(name = "Failed", value = str(failed))
        await inter.response.send_message(embed = embed, ephemeral=True)
    
class RedeemView(discord.ui.View):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(timeout=None)

    @discord.ui.button(label="Redeem")
    async def redeem(self, but, inter):
        match = [role.id for role in inter.user.roles if role.id in (bronze_user_role,)]
        if not match:
            return await inter.response.send_message("You may not redeem this reward!", ephemeral=True)
        check = await self.bot.redis.exists(f"redeem-{inter.user.id}")
        if check:
            return await inter.response.send_message("You have already redeemed this free upvote in the past 24 hours", ephemeral=True)
        
        check = await self.bot.redis.get(f"vote_lock:{inter.user.id}")
        if not check:
            return await inter.response.send_message("You have not yet voted for a bot on Fates List yet!", ephemeral=True)
        await self.bot.redis.delete(f"vote_lock:{inter.user.id}")
        await self.bot.redis.set(f"redeem-{inter.user.id}", 0, ex=60*60*24)
        return await inter.response.send_message("Redeemed. You now have one free upvote!", ephemeral=True)

class Roles(commands.Cog):
    """Commands to handle the role menu"""
    def __init__(self, bot):
        self.bot = bot
        asyncio.create_task(self._cog_load())
   
    async def _cog_load(self):
        await self.bot.wait_until_ready()
        channel = self.bot.get_channel(role_channel)
        return await self._rolemenu(channel, False)
    
    async def _rolemenu(self, channel, public):
        try:
            await channel.purge(limit=100, check=lambda m: (not m.pinned or m.author.id == self.bot.user.id))
        except Exception as exc:
            print(exc, "...retrying")
            return await self._rolemenu(channel, public)
        roles = {"ilovepings": ilovepings_role, "addbotping": addbotping_role, "newsping": newsping_role, "giveaway": giveaway_role}
        view = RoleMenu(bot=self.bot, public=public, roles=roles)
        embed = Embed(title="Fates List Roles", description="Hey there 👋! Please grab your roles here. Use +roles for Bot/Certified Developer roles!")
        msg = await channel.send(embed=embed, view=view)
        view.msg = msg
        await channel.send("If you have the Bronze User role, you can redeem it for a free upvote every 24 hours here!", view=RedeemView(self.bot))
        await channel.send("Click the button below to get the Bot/Certified Developer roles if you don't already have it!", view=_GetRolesView(self.bot))