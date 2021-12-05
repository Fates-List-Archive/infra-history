import discord
from lynxfall.utils.string import get_token

from .cache import *
from .events import *
from .helpers import *
from .imports import *
from .ipc import redis_ipc_new
from .permissions import *


class BotActions():
    def __init__(self, db, bot):
        self.db = db
        self.__dict__.update(bot) # Add all kwargs to class
        logger.debug("Request Acknowledged")

    async def base_check(self) -> Optional[str]:
        """Perform basic checks for adding/editting bots. A check returning None means success, otherwise error should be returned to client"""
        if self.prefix and len(self.prefix) > 9:
            return "Prefix must be less than 9 characters long"

        if not self.vanity:
            return "You must have a vanity for your bot. This can be your username. You can prefix it with _ (underscore) if you don't want the extra growth from it. For example _mewbot would disable the mewbot vanity"

        if self.tags == "":
            return "You must select tags for your bot" #Check tags

        if self.invite:
            if self.invite.startswith("P:"): # Check if perm auto is specified
                perm_num = self.invite.split(":")[1].split("|")[0]
                try:
                    perm_num = int(perm_num)
                except ValueError:
                    return "Invalid Bot Invite: Your permission number must be a integer", 4 # Invalid Invite
            elif not self.invite.startswith("https://discord.com") or "oauth" not in self.invite:
                return "Invalid Bot Invite: Your bot invite must be in the format of https://discord.com/api/oauth2... or https://discord.com/oauth2..." # Invalid Invite

        if len(self.description) > 110:
            return "Your short description must be shorter than 110 characters" # Short Description Check

        if len(self.long_description) < 300:
            return "Your long description must be at least 300 characters long"

        bot_obj = await get_bot(self.bot_id) # Check if bot exists

        if not bot_obj:
            return "According to Discord's API and our cache, your bot does not exist. Please try again after 2 hours."
        
        for tag in self.tags:
            if tag not in TAGS:
                return "One of your tags doesn't exist internally. Please check your tags again" # Check tags internally

        if not self.tags:
            return "You must select tags for your bot" # No tags found

        imgres = None
        
        for banner_key in ("banner_page", "banner_card"):
            banner = self.__dict__[banner_key]
            banner_name = banner_key.replace("_", " ")
            if banner:
                banner = ireplacem((("(", ""), (")", ""), ("http://", "https://")), banner)
                if not banner.startswith("https://"):
                    return f"Your {banner_name} does not use the secure protocol (https://). Please change it" # Check banner and ensure HTTPS
                try:
                    async with aiohttp.ClientSession() as sess:
                        async with sess.head(banner, timeout=30) as res:
                            if res.status != 200:
                                # Banner URL does not support head, try get
                                async with sess.get(self.banner, timeout=30) as res_fallback:
                                    if res_fallback.status != 200:
                                        return f"Could not download {banner_name} using either GET or HEAD! Is your URL correct?"
                                    imgres = res_fallback
                            else:
                                imgres = res
                except Exception as exc:
                    return f"Something wrong happened when trying to get the url for {banner_name}: {exc}"
            
                ct = imgres.headers.get("Content-Type", "").replace(" ", "")
                if ct.split("/")[0] != "image":
                    return f"A banner has an issue: {banner_name} is not an image. Please make sure it is setting the proper Content-Type. Got status code {imgres.status} and content type of {ct}."

        if self.donate and not self.donate.startswith(("https://patreon.com", "https://paypal.me", "https://www.buymeacoffee.com")):
            return "Only Patreon, PayPal.me and Buymeacoffee are supported for donations at this time} You can request for more on our support server!" 
        
        for eo in self.extra_owners:
            tmp = await get_user(eo)
            if not tmp:
                return "One of your extra owners doesn't exist"

        if self.github and not self.github.startswith("https://www.github.com"): # Check github for github.com if not empty string
            return "Your github link must start with https://www.github.com"

        if self.privacy_policy:
            self.privacy_policy = self.privacy_policy.replace("http://", "https://") # Force https on privacy policy
            if not self.privacy_policy.startswith("https://"): # Make sure we actually have a HTTPS privacy policy
                return "Your privacy policy must be a proper URL starting with https://. URLs which start with http:// will be automatically converted to HTTPS while adding"
        check = await vanity_check(self.bot_id, self.vanity) # Check if vanity is already being used or is reserved
        if check:
            return "The custom vanity URL you are trying to get is already in use or is reserved"
        if self.webhook_secret and len(self.webhook_secret) < 8:
            return "Your webhook secret must be at least 8 characters long"

    async def edit_check(self):
        """Perform extended checks for editting bots"""
        check = await self.base_check() # Initial base checks
        if check is not None:
            return check
        
        lock = await self.db.fetchval("SELECT lock FROM bots WHERE bot_id = $1", int(self.bot_id))
        lock = enums.BotLock(lock)
        if lock != enums.BotLock.unlocked:
            return f"This bot cannot be edited as it has been locked with a code of {int(lock)}: ({lock.__doc__}). If this bot is not staff locked, join the support server and run /unlock <BOT> to unlock it."

        check = await is_bot_admin(int(self.bot_id), int(self.user_id)) # Check for owner
        if not check:
            return "You aren't the owner of this bot."

        check = await get_user(self.user_id)
        if check is None: # Check if owner exists
            return "You do not exist on the Discord API. Please wait for a few hours and try again"

    async def add_check(self):
        """Perform extended checks for adding bots"""
        check = await self.base_check() # Initial base checks
        if check is not None:
            return check # Base check erroring means return base check without continuing as string return means error

        if (await self.db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1", self.bot_id)) is not None:
            return "This bot already exists on Fates List" # Dont add bots which already exist

    async def add_bot(self):
        """Add a bot"""
        check = await self.add_check() # Perform add bot checks
        if check:
            return check # Returning a string and not None means error to be returned to consumer

        async with self.db.acquire() as connection: # Acquire a connection
            async with connection.transaction() as tr: # Make a transaction to avoid data loss
                await connection.execute("DELETE FROM bots WHERE bot_id = $1", self.bot_id)
                await connection.execute("DELETE FROM bot_owner WHERE bot_id = $1", self.bot_id)
                await connection.execute("DELETE FROM vanity WHERE redirect = $1", self.bot_id)
                await connection.execute("DELETE FROM bot_tags WHERE bot_id = $1", self.bot_id)
                await connection.execute("""INSERT INTO bots (
                    bot_id, prefix, bot_library,
                    invite, website, banner_card, banner_page,
                    discord, long_description, description,
                    api_token, features, long_description_type, 
                    css, donate, github,
                    webhook, webhook_type, webhook_secret,
                    privacy_policy, nsfw, keep_banner_decor, 
                    id) VALUES(
                    $1, $2, $3,
                    $4, $5, $6,
                    $7, $8, $9,
                    $10, $11, $12, 
                    $13, $14, $15, 
                    $16, $17, $18, 
                    $19, $20, $21, 
                    $22, $1)""", 
                    self.bot_id, self.prefix, self.library, 
                    self.invite, self.website, self.banner_card, self.banner_page,
                    self.support, self.long_description, self.description,
                    get_token(132), self.features, self.long_description_type,
                    self.css, self.donate, self.github, self.webhook, self.webhook_type, self.webhook_secret,
                    self.privacy_policy, self.nsfw, self.keep_banner_decor
                ) # Add new bot info
    
                await connection.execute("INSERT INTO vanity (type, vanity_url, redirect) VALUES ($1, $2, $3)", enums.Vanity.bot, self.vanity, self.bot_id) # Add new vanity if not empty string

                await connection.execute("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", self.bot_id, self.user_id, True) # Add new main bot owner
                extra_owners_fixed = []
                for owner in self.extra_owners:
                    if owner in extra_owners_fixed:
                        continue
                    extra_owners_fixed.append(owner)
                extra_owners_add = [(self.bot_id, owner, False) for owner in extra_owners_fixed] # Create list of extra owner tuples for executemany executemany
                await connection.executemany("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", extra_owners_add) # Add in one step

                tags_fixed = []
                for tag in self.tags:
                    if tag in tags_fixed:
                        continue
                    tags_fixed.append(tag)

                tags_add = [(self.bot_id, tag) for tag in tags_fixed] # Get list of bot_id, tag tuples for executemany    
                await connection.executemany("INSERT INTO bot_tags (bot_id, tag) VALUES ($1, $2)", tags_add) # Add all the tags to the database

        await bot_add_event(self.bot_id, enums.APIEvents.bot_add, {}) # Send a add_bot event to be succint and complete 
        owner = int(self.user_id)            
        bot_name = (await get_bot(self.bot_id))["username"]

        add_embed = discord.Embed(
            title="New Bot!", 
            description=f"<@{owner}> added the bot <@{self.bot_id}>({bot_name}) to queue!", 
            color=0x00ff00,
            url=f"https://fateslist.xyz/bot/{self.bot_id}"
        )
        msg = {"content": f"<@&{staff_ping_add_role}>", "embed": add_embed.to_dict(), "channel_id": str(bot_logs), "mention_roles": [str(staff_ping_add_role)]}
        await redis_ipc_new(redis_db, "SENDMSG", msg=msg, timeout=None)




    async def edit_bot(self):
        """Edit a bot"""
        check = await self.edit_check() # Perform edit bot checks
        if check:
            return check

        async with self.db.acquire() as connection: # Acquire a connection
            async with connection.transaction() as tr: # Make a transaction to avoid data loss
                await connection.execute(
                    "UPDATE bots SET bot_library=$2, webhook=$3, description=$4, long_description=$5, prefix=$6, website=$7, discord=$8, banner_card=$9, invite=$10, github = $11, features = $12, long_description_type = $13, webhook_type = $14, css = $15, donate = $16, privacy_policy = $17, nsfw = $18, webhook_secret = $19, banner_page = $20, keep_banner_decor = $21 WHERE bot_id = $1",  # pylint: disable=line-too-long 
                    self.bot_id, self.library, self.webhook, self.description, self.long_description, self.prefix, self.website, self.support, self.banner_card, self.invite, self.github, self.features, self.long_description_type, self.webhook_type, self.css, self.donate, self.privacy_policy, self.nsfw, self.webhook_secret, self.banner_page, self.keep_banner_decor  # pyline: disable=line-too-long
                ) # Update bot with new info

                await connection.execute("DELETE FROM bot_owner WHERE bot_id = $1 AND main = false", self.bot_id) # Delete all extra owners
                done = []
                for owner in self.extra_owners:
                    if owner in done:
                        continue
                    await connection.execute("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", self.bot_id, owner, False)
                    done.append(owner)

                await connection.execute("DELETE FROM bot_tags WHERE bot_id = $1", self.bot_id) # Delete all bot tags
                done = []
                for tag in self.tags:
                    if tag in done:
                        continue
                    await connection.execute("INSERT INTO bot_tags (bot_id, tag) VALUES ($1, $2)", self.bot_id, tag) # Insert new bot tags
                    done.append(tag)

                check = await connection.fetchrow("SELECT vanity FROM vanity WHERE redirect = $1", self.bot_id) # Check vanity existance
                if check is None:
                    if self.vanity.replace(" ", "") != '': # If not there for this bot, insert new one
                        await connection.execute("INSERT INTO vanity (type, vanity_url, redirect) VALUES ($1, $2, $3)", 1, self.vanity, self.bot_id)
                else:
                    await connection.execute("UPDATE vanity SET vanity_url = $1 WHERE redirect = $2", self.vanity, self.bot_id) # Update the vanity since bot already use it
        await bot_add_event(self.bot_id, enums.APIEvents.bot_edit, {"user": str(self.user_id)}) # Send event
        edit_embed = discord.Embed(
            title="Bot Edit!", 
            description=f"<@{self.user_id}> has edited the bot <@{self.bot_id}>!", 
            color=0x00ff00,
            url=f"https://fateslist.xyz/bot/{self.bot_id}"
        )
        msg = {"content": "", "embed": edit_embed.to_dict(), "channel_id": str(bot_logs), "mention_roles": []}
        await redis_ipc_new(redis_db, "SENDMSG", msg=msg, timeout=None)


