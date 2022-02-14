import discord
from lynxfall.utils.string import get_token
#from lynxfall.utils.string import ireplacem

from .system import FatesWorkerSession

from .cache import *
from .helpers import *
from .ipc import redis_ipc_new
from .auth import *

class BotActions():
    def __init__(self, worker_session: FatesWorkerSession, bot):
        self.db: asyncpg.Pool = worker_session.postgres
        self.redis = worker_session.redis
        self.worker_session = worker_session
        self.__dict__.update(bot) # Add all kwargs to class
        logger.debug("Request Acknowledged")

    async def base_check(self, mode: str) -> Optional[str]:
        """Perform basic checks for adding/editting bots. A check returning None means success, otherwise error should be returned to client"""
        logger.info(self.css)
        if mode == "add":
            state = await self.db.fetchval("SELECT state FROM bots WHERE bot_id = $1", self.bot_id)
            if state is not None:
                if state in (enums.BotState.denied, enums.BotState.banned):
                    return f"This bot has been banned or denied from Fates List.<br/><br/>If you own this bot and wish to appeal this, click <a href='/bot/{self.bot_id}/settings#actions-button-fl'>here</a>"
                return "This bot already exists on Fates List" # Dont add bots which already exist
        
        if self.system_bot:
            if not (await is_staff(None, self.user_id, 5, redis=self.redis))[0]:
                if mode == "edit":
                    return "It seem's like you wish to claim this bot. In order to do so, hou must set 'System Bot' to 'No'/false"
                return "Only staff (Head Admin+) may add system bots"
            
        if self.prefix and len(self.prefix) > 9:
            return "Prefix must be less than 9 characters long"

        if not self.vanity:
            return "You must have a vanity for your bot. This can be your username. You can prefix it with _ (underscore) if you don't want the extra growth from it. For example _mewbot would disable the mewbot vanity"

        check = await self.db.fetchval("SELECT client_id FROM bots WHERE bot_id = $1", self.bot_id)
        if check and self.client_id != str(check):
            return "Client ID cannot change once set"
        self.japi_json = {}


        if not check or mode == "add":
            headers = {"Authorization": japi_key} # Lets hope this doesnt break shit
            async with aiohttp.ClientSession() as sess:
                async with sess.get(f"https://japi.rest/discord/v1/application/{self.bot_id}", headers=headers) as resp:
                    if resp.status != 200 and resp.status != 400:
                        logger.info(f"Got japi status code: {resp.status}")
                        return "japi.rest seems to be down right now. Please contact Fates List Support if you keep getting this error!"
                    self.japi_json = await resp.json()
                    if self.japi_json["data"].get("code") and not self.client_id:
                        return "You need to input a client ID for this bot! You can find this in the Discord Developer Portal"
                    self.client_id = self.bot_id if not self.client_id else self.client_id
                if self.client_id and self.client_id != self.bot_id:
                    async with sess.get(f"https://japi.rest/discord/v1/application/{self.client_id}", headers=headers) as resp:
                        if resp.status != 200 and resp.status != 400:
                            return "japi.rest seems to be down right now. Please contact Fates List Support if you keep getting this error!"
                        self.japi_json = await resp.json()
                        if self.japi_json["data"].get("code"):
                            return "Invalid client ID inputted"
                        if self.japi_json["data"].get("bot", {}).get("id") != str(self.bot_id):
                            return "Invalid client ID for this bot! "

        if self.client_id:
            self.client_id = int(self.client_id)

        if self.tags == "":
            return "You must select tags for your bot" #Check tags

        if self.invite:
            if self.invite.startswith("P:"): # Check if perm auto is specified
                perm_num = self.invite.split(":")[1].split("|")[0]
                try:
                    perm_num = int(perm_num)
                except ValueError:
                    return "Invalid Bot Invite: Your permission number must be a integer", 4 # Invalid Invite
            #elif not self.invite.startswith("https://discord.com") or "oauth" not in self.invite:
            #    state = await db.fetchval("SELECT state FROM bots WHERE bot_id = $1", self.bot_id)
            #    if not self.system_bot and state != enums.BotState.certified:
            #        return "Invalid Bot Invite: Your bot invite must be in the format of https://discord.com/api/oauth2... or https://discord.com/oauth2..." # Invalid Invite

        if len(self.description) > 110 and not self.system_bot:
            return "Your short description must be shorter than 110 characters" # Short Description Check

        if "*" in self.description or "_" in self.description or "`" in self.description:
            return "Your short description may not have *, ` or _"

        if len(self.long_description) < 300 and not self.system_bot:
            return "Your long description must be at least 300 characters long"

        bot_obj = await get_bot(self.bot_id, worker_session=self.worker_session) # Check if bot exists

        if not bot_obj:
            return "According to Discord's API and our cache, your bot does not exist. Please try again after 2 hours."
        
        tags_fixed = []

        for tag in self.tags:
            if tag not in self.worker_session.tags:
                # Merely ignore the tag, autocomplete exists
                continue
            tags_fixed.append(tag)
        self.tags = tags_fixed

        if not self.tags:
            return "You must select tags for your bot" # No tags found

        features_fixed = []
        for _feature in self.features:
            if _feature not in features.keys():
                continue
            features_fixed.append(_feature)
        self.features = features_fixed

        imgres = None
        
        for banner_key in ("banner_page", "banner_card"):
            banner = self.__dict__.get(banner_key, "")
            banner_name = banner_key.replace("_", " ")
            if banner:
                banner = ireplacem((("(", ""), (")", ""), ("http://", "https://")), banner)
                if not banner.startswith("https://"):
                    return f"Your {banner_name} does not use the secure protocol (https://). Please change it" # Check banner and ensure HTTPS
                try:
                    async with aiohttp.ClientSession() as sess:
                        async with sess.head(banner) as res:
                            if res.status != 200:
                                # Banner URL does not support head, try get
                                async with sess.get(banner) as res_fallback:
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
            tmp = await get_user(eo, worker_session=self.worker_session)
            if not tmp:
                return "One of your extra owners doesn't exist"

        if self.github and not self.github.startswith("https://www.github.com"): # Check github for github.com if not empty string
            return "Your github link must start with https://www.github.com"

        if self.privacy_policy:
            self.privacy_policy = self.privacy_policy.replace("http://", "https://") # Force https on privacy policy
            if not self.privacy_policy.startswith("https://"): # Make sure we actually have a HTTPS privacy policy
                return "Your privacy policy must be a proper URL starting with https://. URLs which start with http:// will be automatically converted to HTTPS while adding"
        check = await vanity_bot(self.db, self.redis, self.vanity, ignore_prefix=True)
        if check and check[0] != self.bot_id or self.vanity in reserved_vanity:
            return f"The custom vanity URL you are trying to get is already in use or is reserved ({check})"
        if self.webhook_secret and len(self.webhook_secret) < 8:
            return "Your webhook secret must be at least 8 characters long"

        await self.redis.delete(f"botpagecache:{self.bot_id}")

    async def edit_check(self):
        """Perform extended checks for editing bots"""
        check = await self.base_check("edit") # Initial base checks
        if check is not None:
            return check
        
        flags = await self.db.fetchval("SELECT flags FROM bots WHERE bot_id = $1", int(self.bot_id))
        if flags_check(flags, (enums.BotFlag.staff_locked, enums.BotFlag.edit_locked)):
            return "This bot cannot be edited as it has been locked (see Bot Settings). Join the support server and run /unlock <BOT> to unlock it."

        check = await is_bot_admin(int(self.bot_id), int(self.user_id), worker_session=self.worker_session) # Check for owner
        if not check:
            return "You aren't the owner of this bot."

        check = await get_user(self.user_id, worker_session=self.worker_session)
        if check is None: # Check if owner exists
            return "You do not exist on the Discord API. Please wait for a few hours and try again"

    async def add_check(self):
        """Perform extended checks for adding bots"""
        check = await self.base_check("add") # Initial base checks
        if check is not None:
            return check # Base check erroring means return base check without continuing as string return means error

    async def add_bot(self):
        """Add a bot"""
        check = await self.add_check() # Perform add bot checks
        if check:
            return check # Returning a string and not None means error to be returned to consumer

        approx_guild_count = self.japi_json["data"]["bot"]["approximate_guild_count"]

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
                    client_id, guild_count, flags, page_style, id) VALUES(
                    $1, $2, $3,
                    $4, $5, $6,
                    $7, $8, $9,
                    $10, $11, $12, 
                    $13, $14, $15, 
                    $16, $17, $18, 
                    $19, $20, $21, 
                    $22, $23, $24, $25, $26, $1)""", 
                    self.bot_id, self.prefix, self.library, 
                    self.invite, self.website, self.banner_card, self.banner_page,
                    self.support, self.long_description, self.description,
                    get_token(132), self.features, self.long_description_type,
                    self.css, self.donate, self.github, self.webhook, self.webhook_type, self.webhook_secret,
                    self.privacy_policy, self.nsfw, self.keep_banner_decor, self.client_id, approx_guild_count,
                    [enums.BotFlag.system] if self.system_bot else [], self.page_style
                ) # Add new bot info
   
                if self.system_bot:
                    await connection.execute("UPDATE bots SET flags = flags || $1 WHERE bot_id = $2", [enums.BotFlag.system], self.bot_id)

                await connection.execute("INSERT INTO vanity (type, vanity_url, redirect) VALUES ($1, $2, $3)", enums.Vanity.bot, self.vanity, self.bot_id) # Add new vanity if not empty string

                if not self.system_bot:
                    await connection.execute("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", self.bot_id, self.user_id, True) # Add new main bot owner
                else:
                    await connection.execute("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", self.bot_id, self.extra_owners[0], True)
                    await connection.execute("UPDATE bots set state = $1 WHERE bot_id = $2", enums.BotState.approved, self.bot_id)
                    self.extra_owners = self.extra_owners[1:] + [self.user_id]
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

        await bot_add_event(self.redis, self.bot_id, enums.APIEvents.bot_add, {}) # Send a add_bot event to be succint and complete 
        owner = int(self.user_id)            
        bot_name = (await get_bot(self.bot_id, worker_session=self.worker_session))["username"]

        add_embed = discord.Embed(
            title="New Bot!", 
            description=f"<@{owner}> added the bot <@{self.bot_id}>({bot_name}) to queue!", 
            color=0x00ff00,
            url=f"https://fateslist.xyz/bot/{self.bot_id}"
        )

        add_embed.add_field(name="Guild Count (approx.)", value=approx_guild_count)
        msg = {"content": f"<@&{staff_ping_add_role}>", "embed": add_embed.to_dict(), "channel_id": str(bot_logs), "mention_roles": [str(staff_ping_add_role)]}
        if not self.system_bot:
            await redis_ipc_new(self.redis, "SENDMSG", msg=msg, timeout=None, worker_session=self.worker_session)


    async def edit_bot(self):
        """Edit a bot"""
        check = await self.edit_check() # Perform edit bot checks
        if check:
            return check

        async with self.db.acquire() as connection: # Acquire a connection
            async with connection.transaction() as tr: # Make a transaction to avoid data loss
                await connection.execute(
                    "UPDATE bots SET bot_library=$2, webhook=$3, description=$4, long_description=$5, prefix=$6, website=$7, discord=$8, banner_card=$9, invite=$10, github = $11, features = $12, long_description_type = $13, webhook_type = $14, css = $15, donate = $16, privacy_policy = $17, nsfw = $18, webhook_secret = $19, banner_page = $20, keep_banner_decor = $21, client_id = $22, page_style = $23 WHERE bot_id = $1",  # pylint: disable=line-too-long 
                    self.bot_id, self.library, self.webhook, self.description, self.long_description, self.prefix, self.website, self.support, self.banner_card, self.invite, self.github, self.features, self.long_description_type, self.webhook_type, self.css, self.donate, self.privacy_policy, self.nsfw, self.webhook_secret, self.banner_page, self.keep_banner_decor, self.client_id, self.page_style  # pyline: disable=line-too-long
                ) # Update bot with new info

                flags = await connection.fetchval("SELECT flags FROM bots WHERE bot_id = $1", self.bot_id)
                flags = set(flags)
                if self.system_bot:
                    flags.add(enums.BotFlag.system)
                else:
                    flags.discard(enums.BotFlag.system)
                await connection.execute("UPDATE bots SET flags = $1 WHERE bot_id = $2", list(flags), self.bot_id)

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
                await connection.execute("INSERT INTO user_bot_logs (user_id, bot_id, action) VALUES ($1, $2, $3)", self.user_id, self.bot_id, enums.UserBotAction.edit_bot)
        await bot_add_event(self.redis, self.bot_id, enums.APIEvents.bot_edit, {"user": str(self.user_id)}) # Send event
        edit_embed = discord.Embed(
            title="Bot Edit!", 
            description=f"<@{self.user_id}> has edited the bot <@{self.bot_id}>!", 
            color=0x00ff00,
            url=f"https://fateslist.xyz/bot/{self.bot_id}"
        )
        msg = {"content": "", "embed": edit_embed.to_dict(), "channel_id": str(bot_logs), "mention_roles": []}
        if not self.system_bot:
            await redis_ipc_new(self.redis, "SENDMSG", msg=msg, timeout=None, worker_session=self.worker_session)
