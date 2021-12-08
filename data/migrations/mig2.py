from modules.models import enums
import orjson
import datetime

async def apply(postgres, redis, logger):
    users = await postgres.fetch("SELECT user_id, bot_logs FROM users")
    for user in users:
        logs = orjson.loads(user["bot_logs"])
        for state, val in logs.items():
            if int(state) == enums.BotState.approved.value: action = enums.UserBotAction.approve
            elif int(state) == enums.BotState.denied.value: action = enums.UserBotAction.deny
            elif int(state) == enums.BotState.under_review.value: action = enums.UserBotAction.claim 
            elif int(state) == enums.BotState.certified.value: action = enums.UserBotAction.certify
            else: action = None

            if not action:
                print("continue")
                continue
            for bot in val:
                await postgres.execute("INSERT INTO user_bot_logs (user_id, bot_id, action_time, action) VALUES ($1, $2, $3, $4)", int(user["user_id"]), int(bot["id"]), datetime.datetime.fromtimestamp(bot["ts"]), action)
