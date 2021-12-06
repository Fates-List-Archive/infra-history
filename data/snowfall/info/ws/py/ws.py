# Simple library-esque to handle websockets

import asyncio
import json
import sys
import time
import uuid

import websockets

from modules.models import enums

sys.path.append(".")
sys.path.append("../../../")

URL = "wss://fateslist.xyz/api/dragon/ws/"


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
        async with websockets.connect(URL) as self.websocket:
            while True:
                event = await self.websocket.recv()
                await self._render_event(event)

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
        elif self.data["m"]["e"] == 71 and not self.bot:
            return Vote(self.data["ctx"]["user"], self.data["ctx"]["test"])
        return None
