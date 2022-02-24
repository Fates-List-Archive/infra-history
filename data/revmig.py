import asyncpg

async def apply(postgres, redis, logger):
    reviews = await postgres.fetch("SELECT id, replies FROM reviews")
    for review in reviews:
        if review["replies"]:
            for reply_id in review["replies"]:
                await postgres.execute("UPDATE reviews SET parent_id = $1 WHERE id = $2",review["id"], reply_id)
                print(review, reply_id)
