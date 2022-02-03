import asyncio
import time
import uuid
import warnings
from typing import Sequence
import orjson
from loguru import logger

async def redis_ipc_new(
    redis,
    cmd: str, 
    msg: str = None, 
    timeout: int = 30, 
    args: Sequence[str] = None, 
    no_wait: bool = False,
    *,
    worker_session = None
):
    if worker_session:
        app = worker_session.app
    else:
        logger.debug("No worker_session passed to redis_ipc_new")
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
                try:
                    if worker_session:
                        app.state.worker_session.up = True # If we have data, then IPC is up
                except AttributeError:
                    pass
                return data

        if not no_wait:
            if worker_session:
                await app.state.wait_for_ipc()
            return await redis_ipc_new(redis, cmd, msg=msg, timeout=timeout, args=args.split(" "), no_wait=True, worker_session=worker_session)

    if timeout:
        return await wait(cmd_id)
    return None
