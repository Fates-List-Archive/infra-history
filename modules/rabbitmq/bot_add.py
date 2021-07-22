from modules.core import *
from lynxfall.rabbit.core import *

class Config:
    queue = "bot_add_queue"
    name = "Bot Add"
    description = "Adds a bot to the queue"

async def backend(state, json, *, user_id, bot_id, prefix, library, website, banner_card, banner_page, support, long_description, description, tags, extra_owners, invite, features, long_description_type, css, donate, github, webhook, webhook_type, webhook_secret, vanity, privacy_policy, nsfw, keep_banner_decor, **kwargs):
    user_id, bot_id = int(user_id), int(bot_id) # I am stupid and made this a string
    logger.debug(f"Got bot id {bot_id}")
    await state.postgres.execute("DELETE FROM bots WHERE bot_id = $1", bot_id)
    await state.postgres.execute("DELETE FROM bot_owner WHERE bot_id = $1", bot_id)
    await state.postgres.execute("DELETE FROM vanity WHERE redirect = $1", bot_id)
    await state.postgres.execute("DELETE FROM bot_tags WHERE bot_id = $1", bot_id)
    await state.postgres.execute("""INSERT INTO bots (
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
            bot_id, prefix, library, 
            invite, website, banner_card, banner_page,
            support, long_description, description,
            get_token(132), features, long_description_type,
            css, donate, github, webhook, webhook_type, webhook_secret,
            privacy_policy, nsfw, keep_banner_decor) # Add new bot info
    if vanity and vanity.replace(" ", ""):
        await state.postgres.execute("INSERT INTO vanity (type, vanity_url, redirect) VALUES ($1, $2, $3)", enums.Vanity.bot, vanity, bot_id) # Add new vanity if not empty string


    async with state.postgres.acquire() as connection: # Acquire a connection
        async with connection.transaction() as tr: # Use a transaction to prevent data loss
            await connection.execute("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", bot_id, user_id, True) # Add new main bot owner
            extra_owners_fixed = []
            for owner in extra_owners:
                if owner in extra_owners_fixed:
                    continue
                extra_owners_fixed.append(owner)
            extra_owners_add = [(bot_id, owner, False) for owner in extra_owners_fixed] # Create list of extra owner tuples for executemany executemany
            await connection.executemany("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", extra_owners_add) # Add in one step

    async with state.postgres.acquire() as connection: # Acquire a connection
        async with connection.transaction() as tr: # Use transaction to prevent data loss
            tags_fixed = []
            for tag in tags:
                if tag in tags_fixed:
                    continue
                tags_fixed.append(tag)
            tags_add = [(bot_id, tag) for tag in tags_fixed] # Get list of bot_id, tag tuples for executemany
            
            await connection.executemany("INSERT INTO bot_tags (bot_id, tag) VALUES ($1, $2)", tags_add) # Add all the tags to the database

    await bot_add_event(bot_id, enums.APIEvents.bot_add, {}) # Send a add_bot event to be succint and complete 
    owner = int(user_id)
    channel = state.client.get_channel(bot_logs)
    bot_name = (await get_bot(bot_id))["username"]
    add_embed = discord.Embed(title="New Bot!", description=f"<@{owner}> added the bot <@{bot_id}>({bot_name}) to queue!", color=0x00ff00)
    add_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{bot_id}")
    try:
        member = channel.guild.get_member(owner)
        if member is not None:
            await member.send(embed = add_embed) # Send user DM if possible
    except:
        pass
    await channel.send(f"<@&{staff_ping_add_role}>", embed = add_embed) # Send message with add bot ping
