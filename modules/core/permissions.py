"""
Permission Related Code
"""

from .imports import *
from .ipc import *

class StaffMember(BaseModel):
    """Represents a staff member in Fates List""" 
    name: str
    id: Union[str, int]
    perm: int
    staff_id: Union[str, int]

async def is_staff_unlocked(bot_id: int, user_id: int):
    return await redis_db.exists(f"fl_staff_access-{user_id}:{bot_id}")

async def is_bot_admin(bot_id: int, user_id: int):
    try:
        user_id = int(user_id)
    except ValueError:
        return False
    if (await is_staff(staff_roles, user_id, 4))[0] and (await is_staff_unlocked(bot_id, user_id)):
        return True
    check = await db.fetchval("SELECT COUNT(1) FROM bot_owner WHERE bot_id = $1 AND owner = $2", bot_id, user_id)
    if check == 0:
        return False
    return True

async def is_staff(staff_json: dict | None, user_id: int, base_perm: int, json: bool = False, *, redis=None) -> Union[bool, int, StaffMember]:
    redis = redis if redis else redis_db
    if user_id < 0: 
        staff_perm = None
    else:
        staff_perm = await redis_ipc_new(redis, "GETPERM", args=[str(user_id)])
    if not staff_perm:
        staff_perm = {"fname": "Unknown", "id": "0", "staff_id": "0", "perm": 0}
    else:
        staff_perm = orjson.loads(staff_perm)
    sm = StaffMember(name = staff_perm["fname"], id = staff_perm["id"], staff_id = staff_perm["staff_id"], perm = staff_perm["perm"]) # Initially
    rc = sm.perm >= base_perm
    if json:
        return rc, sm.perm, sm.dict()
    return rc, sm.perm, sm
