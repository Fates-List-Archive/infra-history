# Getting Started

Fates List offers websockets to allow you to get real time stats about your bot. This has been rewritten in golang to allow for better performance and reliability as well as new features that could not be implemented performantly in python

### What are Websockets?

Please read [this nice MDN doc on WebSockets](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API) first before attempting this from scratch. We have example libraries below in case you just want to get it done quickly!

### Receiving Responses

Large responses are seperated using ASCII Code 31 This is ``\x1f`` in python.

Some example code on how to recieve responses from websocket is below:

```py

for m in event.split("\x1f"):
    for e in m.split("\x1f"):
        if e == "":
            continue
        e_json = json.loads(e)
        if e_json.get("m"):
            e_type = e_json["m"].get("e")
            ...
        elif e_json.get("control"):
            ...
        await self.hooks["default"](e_json)
```

### Payloads

Payloads sent by the websocket server are either [events](../structures/event.md) or control payloads.

The format for sending data from the client to the websocket is still being worked on and is not used in any case.

Below is the format for a control payload:

| Key | Description | Type |
| :--- | :--- | :--- |
| chan | The redis channel of the object | String? |
| code | The control payload name. This can be used to check for an identity etc. | String |
| detail | Human friendly information describing the control payload for debugging. May be used in future for non-debugging purposes | String |
| ts | The timestamp in seconds for the event | Integer/Float |
| requests_remaining | The amount of requests remaining before you are ratelimited. Is always -1 in initial identity *for now* | Integer |
| control | Always set to true in a control payload | Boolean |

All other payloads sent to you by websocket will be a event as of right now. This may change in the future.

### Identity

When you recieve a ``identity`` control payload, you should respond with the following format (or as given in the ``detail`` key)

| Key | Description | Type |
| :--- | :--- | :--- |
| id | Bot/Server ID | Snowflake |
| token | API Token | String |
| send_all | Whether or not to send all prior events. This may cause disconnects/instability, more memory usage and ratelimits on large bots | Boolean |
| send_none | Whether or not to send events after sending prior events if ``send_all`` is set | Boolean |
| bot | Set this to true for a bot, otherwise this will default to a guild | Boolean |

After a successful identity, you will now have a established websocket connection. You will then start receiving payloads.

### Simple Libraries

**Python websocket library**

```py
# Simple library-esque to handle websockets

import asyncio
import json
import sys

import websockets

sys.path.append(".")
sys.path.append("../../../")
sys.path.append("/home/meow/FatesList")

URL = "wss://api.fateslist.xyz/api/dragon/ws/"


class Bot:
    def __init__(
        self,
        bot_id: int,
        token: str,
        send_all: bool = True,
        send_none: bool = False,
        bot: bool = True,
    ):
        self.bot_id = bot_id
        self.token = token
        self.send_all = send_all
        self.send_none = send_none
        self.hooks = {
            "ready": self.none,
            "identity": self.identity,
            "default": self.default,
            "event": self._on_event_payload,
        }
        self.websocket = None
        self.bot = bot

    async def _render_event(self, event):
        for m in event.split("\x1f"):
            for e in m.split("\x1f"):
                if e == "":
                    continue
                e_json = json.loads(e)
                await self.hooks["default"](e_json)
                try:
                    await self.hooks[e_json["code"]](e_json)
                except KeyError:
                    ...

    async def _ws_handler(self):
        try:
            async with websockets.connect(URL) as self.websocket:
                while True:
                    event = await self.websocket.recv()
                    await self._render_event(event)
        except websockets.WebSocketException as exc:
            print(f"Got error {exc}. Retrying connection...")
            return await self._ws_handler()


    async def identity(self, event):
        # print(event)
        payload = {
            "id": str(self.bot_id),
            "token": self.token,
            "send_all": self.send_all,
            "send_none": self.send_none,
            "bot": self.bot,
        }
        await self.websocket.send(json.dumps(payload))
        print(f"Sending {json.dumps(payload)}")

    @staticmethod
    async def default(event):
        print(event, type(event))

    async def none(self, event):
        ...

    async def _on_event_payload(self, event):
        await self.on_event(
            EventContext(event["dat"], event["dat"]["m"]["e"], self.bot))

    @staticmethod
    async def on_event(ctx):
        print(ctx.parse_vote())

    def start(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._ws_handler())

    def close(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.websocket.close())


class Vote:
    def __init__(self, user_id: str, test: bool):
        self.user_id = int(user_id)
        self.test = test


class EventContext:
    def __init__(self, data, event, bot):
        self.data: dict = data
        self.event: int = event
        self.bot: bool = bot

    def parse_vote(self) -> Vote:
        """Returns the User ID who voted"""
        if self.data["m"]["e"] == 0 and self.bot:
            return Vote(self.data["ctx"]["user"], self.data["ctx"]["test"])
        if self.data["m"]["e"] == 71 and not self.bot:
            return Vote(self.data["ctx"]["user"], self.data["ctx"]["test"])
```

**Test code**

```py

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
import os

try:
    import dotenv
    dotenv.load_dotenv(".env")
except:
    pass

from modules.models import enums

if os.environ.get("ID"):
    bot_id = int(os.environ.get("ID"))
    api_token = os.environ.get("TOKEN")
else:
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
bot = bot.lower() in ("y", "yes")

bot = ws.Bot(bot_id, api_token, bot = bot)
try:
    bot.start()
except KeyboardInterrupt:
    bot.close()
```

**Javascript (browser only, you will have to port this to NodeJS yourself)**

```js
// This only works in browsers, not NodeJS
class FatesWS {
	constructor(id, token, sendAll, sendNone, bot) {
		this.id = id
		this.token = token
		this.sendAll = sendAll
		this.sendNone = sendNone
		this.bot = bot
		this.hooks = {
			"ready": this.ready,
			"identity": this.identity,
			"fallback": this.fallback,
			"event": this.event
		}
		this.websocket = null
	}

	start() {
		this.websocket = new WebSocket("wss://fateslist.xyz/api/dragon/ws")
		this.websocket.onmessage = (event) => {
			let data = event.data.split("\x1f")
			data.forEach(dat => {
				if(dat == "") {
					// It is possible for the event to be empty so ignore those
					return
				}
				let json = JSON.parse(dat)
				console.log({json}, json.code)
				try {
					let hook = this.hooks[json.code]
					if(hook) {
						hook(this, json)
					} else {
						console.log(json.code, "hook not found")
					}
				}
				catch (error) {
					console.log(error)
					// This is normal do nothing
				}
			})
		}
	}

	ready(cls, data) {
		console.log(data)
	}

	fallback(cls, data) {
		console.log(data)
	}

	identity(cls, data) {
		console.log(data)
		let identityPayload = {
			id: cls.id,
			token: cls.token,
			send_all: cls.sendAll,
			send_none: cls.sendNone,
			bot: cls.bot
		}
		console.log({identityPayload})
		cls.websocket.send(JSON.stringify(identityPayload))
	}

	event(cls, data) {
		console.log(data)
	}

	close(code) {
		if(!code) {
			code = 1000
		}
		this.websocket.close(code)
	}
}

class EventsClass {
	constructor() {
		this.VoteEvent = 0
		this.ViewEvent = 16
		this.InviteEvent = 17
	}
}

var Events = new EventsClass()
```