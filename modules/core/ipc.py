import asyncio
import time
import uuid
import warnings
from typing import Sequence
import orjson
from loguru import logger
import aiohttp

async def redis_ipc_new(
    redis,
    cmd: str, 
    msg: dict = None, 
    timeout: int = 30, 
    args: Sequence[str] = None, 
    no_wait: bool = False,
    *,
    worker_session = None
):
    if cmd == "GETCH":
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f"http://localhost:1234/getch/{args[0]}") as res:
                if res.status == 404:
                    return ""
                return await res.text()
    elif cmd == "SENDMSG":
        msg["channel_id"] = int(msg["channel_id"])
        if not msg.get("embed"):
            msg["embed"] = {"type": "rich", "title": "Baypaw Message"}
        if not msg.get("mention_roles"):
            msg["mention_roles"] = []
        async with aiohttp.ClientSession() as sess:
            async with sess.post(f"http://localhost:1234/messages", json=msg) as res:
                return await res.text()

    args = args if args else []
    cmd_id = str(uuid.uuid4())
    if msg:
        msg_id = str(uuid.uuid4())
        await redis.set(msg_id, orjson.dumps(msg), ex=30)
        args.append(msg_id)
    args = " ".join(args)
    if args:
        await redis.publish("_worker_fates", f"{cmd} {cmd_id} {args}")
    else:
        await redis.publish("_worker_fates", f"{cmd} {cmd_id}")
    
    async def wait(id):
        start_time = time.time()
        while time.time() - start_time < timeout:
            await asyncio.sleep(0)
            data = await redis.get(id)
            if data is not None:
                return data

        if not no_wait:
            return await redis_ipc_new(redis, cmd, msg=msg, timeout=timeout, args=args.split(" "), no_wait=True, worker_session=worker_session)

    if timeout:
        return await wait(cmd_id)
    return None
