from fastapi import Security
import aioredis

from pydantic import BaseModel
from typing import Union
import orjson
from .ipc import *

# Staff Permission Checks

class StaffMember(BaseModel):
    """Represents a staff member in Fates List""" 
    name: str
    id: Union[str, int]
    perm: int
    staff_id: Union[str, int]

async def is_staff_unlocked(bot_id: int, user_id: int, redis: aioredis.Connection):
    return await redis.exists(f"fl_staff_access-{user_id}:{bot_id}")

async def is_staff(staff_json: dict | None, user_id: int, base_perm: int, json: bool = False, *, worker_session = None, redis: aioredis.Connection = None) -> Union[bool, int, StaffMember]:
    if worker_session:
        redis = worker_session.redis
    elif not redis:
        raise ValueError("No redis connection or worker_session provided")
    
    if user_id < 0: 
        staff_perm = None
    else:
        staff_perm = await redis_ipc_new(redis, "GETPERM", args=[str(user_id)], worker_session=worker_session)
    if not staff_perm:
        staff_perm = {"fname": "Unknown", "id": "0", "staff_id": "0", "perm": 0}
    else:
        staff_perm = orjson.loads(staff_perm)
    sm = StaffMember(name = staff_perm["fname"], id = staff_perm["id"], staff_id = staff_perm["staff_id"], perm = staff_perm["perm"]) # Initially
    rc = sm.perm >= base_perm
    if json:
        return rc, sm.perm, sm.dict()
    return rc, sm.perm, sm
