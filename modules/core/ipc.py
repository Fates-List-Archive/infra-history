from typing import Sequence
import aiohttp

async def redis_ipc_new(
    redis,
    cmd: str, 
    msg: dict = None, 
    timeout: int = 30, 
    args: Sequence[str] = None, 
    *_,
    **__,
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
    elif cmd == "ROLES":
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f"https://api.fateslist.xyz/flamepaw/_roles?user_id={args[0]}", json=msg) as res:
                return await res.text()
    elif cmd == "GETPERM":
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f"https://api.fateslist.xyz/flamepaw/_getperm?user_id={args[0]}", json=msg) as res:
                return await res.text()
    return None
