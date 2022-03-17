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
- mode is either ``Bot`` or ``Server`` (case-sensitive)

### Example Program

Here's a example on the above:

```py
#!/usr/bin/env python

import asyncio
import websockets
import asyncio

async def ping(ws):
    while True:
        await ws.send("PING")

        # Wait 20 more seconds
        await asyncio.sleep(20)

async def mock_unsub(ws):
    await asyncio.sleep(60)
    print("Ending GWTASK")
    await ws.send("ENDGWTASK")

async def hello():
    async with websockets.connect("wss://api.fateslist.xyz/ws/519850436899897346?mode=Bot") as websocket:
        # Start ping
        asyncio.create_task(ping(websocket))

        # Subscribe to the pubsub channel
        await websocket.send("SUB")

        # After 60 seconds, this will close the subscription task
        asyncio.create_task(mock_unsub(websocket))

        # Handle messages as well as PING responses by just printing them
        async for msg in websocket:
            if(msg.isdigit()):
                print("GOT PING:", msg)
                continue

            print(msg)

asyncio.run(hello())
```

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
