### Some History

Fates List offers websockets to allow you to get real time stats about your bot. This has been rewritten in golang and now in actix-web to allow for better performance and reliability as well as new features that could not be implemented performantly in python. These docs contain the protocol used and how to actually use WebSockets on Fates List. *The protocol may be rewritten again but this is highly unlikely at this point. The API is stable*


::: warning

While Lynx *does* have it's own WebSocket API for internal use and actually running Lynx. 
External use is probihited without explicit permission from Fates List however you can't
do much anyways without having staff permissions :)

:::

### What are Websockets?

Please read [this nice MDN doc on WebSockets](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API) first before attempting this from scratch. We have example libraries below in case you just want to get it done quickly!

### API v3 note

With API v3, the websocket API was *rewritten* and has been completely changed.

As of right now, not all features have been fully implemented, heres the list of features that will be added soon:

- Archived WS Response views (using a ``ARCHIVE`` command)  

### Too long; didn't read

- Events are now wrapped 
- Subscribe/Archive is no longer implicit
- Archive is coming out
- Addition of "Gateway Tasks" for background tasks spawned by the user

### Gateway Tasks

All user-invokable background tasks are called as "Gateway Tasks". A websocket connection can only have one "Gateway Task" running on it. Make a new connection or stop the existing task using ``ENDGWTASK``.

On creation of a gateway task, ``GWTASK TASK_NAME`` will be sent to you from the spawned background task. *When ending a background task, TASK_NAME will be NONE*. 

If a background task fails to spawn for whatever reason, you will not recieve a ``GWTASK`` message, in this case, do one of the following:

- Unsubsribe from the running task using ``ENDGWTASK``. If a "Gateway Task" is not running however, this will close the websocket with a close code of `4002`.
- Rerun the command thats *supposed* to create a "Gateway Task". If a "Gateway Task" is already running however, this will close the websocket with a close code of `4001`.
- Do nothing as these errors are extremely rare and usually mean a bug in your code. Additionally the task may actually be running but you may have missed the ``GWTASK`` response.

**A websocket connection starts with no tasks running by defauls**. This also means no events are sent to you until you create a task. This is to reduce 'accidental' bogus connections.

If a gateway task (such as ``ARCHIVE``) exits, the gateway task will *still* be considered as spawned until you call ``ENDGWTASK``.

A ``GWTASKACK TASK_NAME`` will be sent in the event a ackable "Gateway Task" finishes. A ackable task is one that can finish or end after a period of time. For example ``ARCHIVE`` is ackable as it ends after it has consumed all archived messages and delivered all that it could deliver.

A general rule of thumb when you're confused as to why something is a "Gateway Task":

- Is it asynchronous?
- Is it long-running?
- Can it overwhelm the client or server if multiple calls to it or a "Gateway Task" is called?
- Will the user want control over its execution (start, stop)

#### Why?

In case anyones confused on why gateway tasks, it was added so large bots don’t struggle with websockets and to allow more control over sent data. 

For example, you can now use ARCHIVE, wait for a specific message or set of messages and then exit with ENDGWTASK instead of needing to process every single event (previous implementations sent archived messages as a hacking chained blob, that has also been fixed meaning you can now choose parse exactly what you need instead of everything)

#### Spawning a Gateway Task

You spawn a "Gateway Task" by just sending it as plaintext just like how you send ``PING``s.

You stop the ongoing "Gateway Task" by sending ``ENDGWTASK``.

After a "Gateway Task" acks, the task itself will have stopped however **the gateway task is *still* considered as running until you explicitly call ``ENDGWTASK``**. This only applies to ackable "Gateway Tasks" as only they can ack.

### Authentication

Websockets right now do *not* need authentication to get real-time stats as such information is public through other means anyways and is not considered sensitive

If sensitive information is added to websockets, an additional ``UPGRADE`` command will be created for these commands, it is not documented here as it does not exist yet.

Authorization may also be readded in the future if needed.

Removal of authorization for now however allows simplification of the protocol.

### Pings

Your websocket client must send a ``PING`` every 20 seconds or it will be disconnected. A ping frame does not count though is still needed, it must be a message frame containing the string ``PING``. 

The server will acknowledge your ``PING`` with a number that is the amount of time (in microseconds) you have been connected to the Websocket. 

This server response is the only case of a number and you should use your languages ``isdigit()`` function to check for pings. The reason for all of this extra complicity is to avoid disconnects and ensure client is properly connected

**The ``PING`` system also applies to the Preview API**

### Gateway Tasks

| Task Name | Description |
| :--- | :--- |
| SUB | *Subscribes* to the redis pubsub channel for events. After creating this task successfully, you will begin recieving real time stats for your bot/server. |
| ARCHIVE | Iterates over all archived events from the beginning of event recording (Wednesday 16th March 11PM) to the current time. Is a ackable "Gateway Task" |

### Base URL

The base URL for api v3 websockets is ``wss://api.fateslist.xyz/ws/{id}?mode={mode}``

- id is a ``i64`` (int64) that is either your Bot ID or your Server ID you wish to connect to websocket API for. **For all practical cases and purposes, id can also be treated as a Discord Snowflake**
- mode is a [TargetType](https://lynx.fateslist.xyz/docs/enums-ref#targettype)

### Event Wrapping

Unless specified otherwise, all events sent over websocket will be JSON just like all other events

Events sent over API v3 websockets are considered to be *wrapped*. That is, the event is wrapped in another key that is the id for the event.

**Example** 

```json
{
    "deba8751-3547-448e-b564-a6ccbc9a00cb": {
        "m": {
            "e":16, 
            "eid": "deba8751-3547-448e-b564-a6ccbc9a00cb"
        }, 
        "ctx": {
            "user": null, 
            "target": "519850436899897346", 
            "target_type": 0, 
            "ts": 1647431531
        }, 
        "props": {
            "widget": false, 
            "vote_page":false, 
            "invite": false
        }
    }
}

```

### A sample python library

```py
from contextlib import asynccontextmanager
import enum
import websockets
import json
import asyncio

class WsMode(enum.Enum):
    bot = 0
    server = 1

class FatesHeader:
    """Represents a command header from WS"""
    def __init__(self, msg: str):
        self.msg = msg
    
    def __str__(self):
        return f"CmdHeader<{self.msg}>"
    
    def __repr__(self):
        return f"<FatesHeader msg={self.msg}>"

class FatesWsConn:
    def __init__(self, ws):
        self.ws = ws
        self.up = True
        self._is_pinging = False
        self.gw_task = None
        self._ping_task = asyncio.create_task(self._ping())
    
    async def _ping(self):
        if self._is_pinging:
            raise RuntimeError("Cannot ping when already pinging!")

        self._is_pinging = True
        while self.up:
            await self.ws.send("PING")
            await asyncio.sleep(20)

    async def end_gw_task(self):
        """Ends a gateway task"""
        await self.ws.send("ENDGWTASK")
        await asyncio.sleep(0.1)
        self.gw_task = None
    
    async def sub(self):
        if self.gw_task:
            raise RuntimeError("GWTask cannot already be running")
        class _Sub():
            def __init__(self, parent):
                self.parent = parent
            def __aiter__(self):
                return self
            async def __anext__(self):
                while True:
                    msg = await self.parent.ws.recv()
                    if msg.isdigit():
                        continue # Is ping, ignore
                    try:
                        return json.loads(msg)
                    except:
                        return FatesHeader(msg)

        self.gw_task = "SUB"
        await self.ws.send("SUB")
        return _Sub(self)

    async def archive(self):
        if self.gw_task:
            raise RuntimeError("GWTask cannot already be running")
        class _Sub():
            def __init__(self, parent):
                self.parent = parent
            def __aiter__(self):
                return self
            async def __anext__(self):
                while True:
                    msg = await self.parent.ws.recv()

                    if msg.isdigit():
                        continue # Is ping, ignore

                    # Handle the final ack
                    if msg == "GWTASKACK ARCHIVE":
                        await self.parent.end_gw_task()
                        raise StopAsyncIteration

                    try:
                        return json.loads(msg)
                    except:
                        return FatesHeader(msg)

        self.gw_task = "ARCHIVE"
        await self.ws.send("ARCHIVE")
        return _Sub(self)

@asynccontextmanager
async def fates_ws(id: int, mode: WsMode):
    async with websockets.connect(f"wss://api.fateslist.xyz/ws/{id}?mode={mode.value}") as websocket:
        conn = FatesWsConn(websocket)
        yield conn
        conn.up = False
```

**Usage Example**

1. Bot subscription example

```py
import test
import asyncio

async def main():
    async with test.fates_ws(519850436899897346, test.WsMode.bot) as bot:
        sub = await bot.sub()
        async for v in sub:
            print(v)
asyncio.run(main())
```

2. Bot archive example

```py
import test
import asyncio

async def main():
    async with test.fates_ws(519850436899897346, test.WsMode.bot) as bot:
        archive = await bot.archive()
        async for v in archive:
            print(v)
asyncio.run(main())
```

3. Bot archive then subscription example

```py
import test
import asyncio

async def main():
    async with test.fates_ws(519850436899897346, test.WsMode.bot) as bot:
        archive = await bot.archive()
        async for v in archive:
            print(v)
        sub = await bot.sub()
        async for v in sub:
            print(v)

asyncio.run(main())
```
