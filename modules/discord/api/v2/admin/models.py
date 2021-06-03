from pydantic import BaseModel, validator
import modules.models.enums as enums
from ..base_models import BaseUser, APIResponse, IDResponse
from typing import Optional, List
import uuid

class BotListAdminRoute(BaseModel):
    mod: str

    @validator('mod')
    def mod_int(cls, v, values, **kwargs):
        if not v.isdigit():
            raise ValueError('Mod must be a integer')
        return int(v)

class BotListPartner(BotListAdminRoute):
    type: enums.PartnerType
    partner: str
    channel: str # Channel for partnership
    invite: str # Support server or partnered server invite
    id: Optional[str] = None
 
    @validator('id')
    def id_if_bot(cls, v, values, **kwargs):
        if values.get("type") != enums.PartnerType.bot:
            return int(v) if v.isdigit() else None
        elif v is None or not v.isdigit():
            raise ValueError('Bots must have a ID set')
        return v

class BotListPartnerAd(BotListAdminRoute):
    mod: str
    pid: uuid.UUID
    ad: str
        
class BotLock(BotListAdminRoute):
    reason: str
    lock: bool

class BotCertify(BotListAdminRoute):
    certify: bool

class BotStateUpdate(BaseModel):
    state: enums.BotState

class BotTransfer(BotListAdminRoute):
    new_owner: str

class BotUnderReview(BotListAdminRoute):
    requeue: enums.BotRequeue

class BotQueuePatch(BotListAdminRoute):
    feedback: Optional[str] = None 
    approve: bool

class PartialBotQueue(BaseModel):
    user: BaseUser
    prefix: str
    invite: str
    description: str

class BotQueueList(BaseModel):
    __root__: List[PartialBotQueue]
class BotQueueGet(BaseModel):
    bots: BotQueueList

class BotBan(BaseModel):
    ban: bool
    reason: Optional[str] = None
    mod: str
