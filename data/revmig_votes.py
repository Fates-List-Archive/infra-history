import asyncpg

async def apply(postgres, redis, logger):
    reviews = await postgres.fetch("SELECT id, review_upvotes, review_downvotes FROM reviews")
    for review in reviews:
        for upvote in review["review_upvotes"]:
            print(upvote)
            await postgres.execute(
                "INSERT INTO review_votes (id, user_id, upvote) VALUES ($1, $2, true)",
                review["id"],
                upvote
            )
        for downvote in review["review_downvotes"]:
            print(downvote)
            await postgres.execute(
                "INSERT INTO review_votes (id, user_id, upvote) VALUES ($1, $2, false)",
                review["id"],
                downvote
            )