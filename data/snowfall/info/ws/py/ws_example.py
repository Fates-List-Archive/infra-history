import asyncio
import json
import time
import uuid
import sys
sys.path.append(".")
sys.path.append("../../../")


# For server testing:
# guild id is 816130947274899487
# guild api token is dkKLvVMoFtFKFpUpCPiREqQsLyMRrEWldwrQeWuYayehfGVJYUKmsupGvRfNbGpoGHVNVjqIWDiBCRrQuDkEuUnPYVfRrNrATIrgzLPbREjRqFpUDqZbAhrPsbaYpPYwsDImGuhoSFgJSxFerBpKWdsKXEzoRkdGDSmQjatievbANVvSDvCETPxgRCKTwgSdbJuRkI


import ws

from modules.models import enums
bot_id = input("Enter Bot ID: ")
try:
    bot_id = int(bot_id)
except ValueError:
    bot_id = 811073947382579200

if bot_id == 811073947382579200:
    api_token = "AzbnMlEABvKnIe3zt6zHMCOGrnoan5tS0hXCfzpBa3UiHdl045p1h5vxivMBtH5UFETZJdQ9TkpoDsy954uia74Hak5KWECqCufjvRZfV66enoB1rHf1HQtk6g04GajKqr98"
else:
    api_token = input("Enter API Token: ")

bot = input("Is this a bot (Y/N): ")
if bot.lower() in ("y", "yes"):
    bot = True
else:
    bot = False

bot = ws.Bot(bot_id, api_token, bot = bot)
try:
    bot.start()
except KeyboardInterrupt:
    bot.close()
