from modules.core import *
from lynxfall.rabbit.core import *


class Config:
    queue = "server_add_queue"
    name = "Add Server"
    description = "Adds a server to Fates List"

async def backend(state, json, *, user_id, guild_id, data, description, long_description_type, long_description, tags, vanity, **kwargs):
    guild_id = int(guild_id)
    guild_name = data.get("name")
    await db.execute("DELETE FROM servers WHERE guild_id = $1", guild_id)
    await db.execute("DELETE FROM vanity WHERE redirect = $1", guild_id)
    await db.execute("INSERT INTO servers (guild_id, name_cached, description, long_description_type, long_description) VALUES ($1, $2, $3, $4, $5)", guild_id, guild_name, description, long_description_type, long_description)

    async with db.acquire() as connection:
        async with connection.transaction() as tr:
            tags_add = [(guild_id, tag) for tag in tags]
            await connection.executemany("INSERT INTO server_tags (guild_id, tag) VALUES ($1, $2)", tags_add)

            if vanity.replace(" ", "") != '':
                await connection.execute("INSERT INTO vanity (type, vanity_url, redirect) VALUES ($1, $2, $3)", enums.Vanity.server, vanity, guild_id) # Add new vanity if not empty string

    add_embed = discord.Embed(title="New Server!", description=f"<@{user_id}> added the server {guild_name} ({guild_id}) to the list!", color=0x00ff00)
    add_embed.add_field(name="Link", value=f"https://fateslist.xyz/server/{guild_id}")
    channel = client.get_channel(server_logs)
    await channel.send(embed = add_embed)
