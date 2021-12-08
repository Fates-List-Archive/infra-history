from modules.models import enums
import json
import time

async def apply(postgres, redis, logger):
    verifiers = await postgres.fetch("SELECT bot_id, verifier, state FROM bots")
    for verifier in verifiers:
        if not verifier["verifier"]:
            continue
        user = verifier["verifier"]
        state = enums.BotState(verifier["state"])
        check = await postgres.fetchval("SELECT bot_logs[$1] FROM users WHERE user_id = $2", str(state.value), user)
        if not check:
            print(f"{user} does not have a bot log for {state} yet. Creating one...")
            await postgres.execute("UPDATE users SET bot_logs = bot_logs || $1 WHERE user_id = $2", json.dumps({str(state.value): [{"id": str(verifier["bot_id"]), "ts": time.time()}]}), user)
        else:
            await postgres.execute("UPDATE users SET bot_logs[$1] = bot_logs[$1] || $2 WHERE user_id = $3", str(state.value), json.dumps([{"id": str(verifier["bot_id"]), "ts": time.time()}]), user)
