import uuid
from typing import List, Optional

from pydantic import BaseModel, validator

import modules.models.enums as enums

from ..base_models import APIResponse, BaseUser


class BotMeta(BaseModel):
    """
    Notes:

    - extra_owners must be a list of strings where the strings
    can be made a integer
    """
    prefix: str
    library: str
    invite: str
    website: Optional[str] = None
    description: str
    banner_card: Optional[str] = None
    banner_page: Optional[str] = None
    keep_banner_decor: bool
    extra_owners: List[str] # List of strings that can be turned into a integer
    support: Optional[str] = None
    long_description: str
    css: Optional[str] = None
    long_description_type: enums.LongDescType
    nsfw: bool
    donate: Optional[str] = None
    privacy_policy: Optional[str] = None
    github: Optional[str] = None
    webhook_type: Optional[int] = 0
    webhook: Optional[str] = None
    webhook_secret: Optional[str] = None
    vanity: str
    features: List[str] = []
    tags: List[str]

    @validator("extra_owners")
    def extra_owner_converter(cls, v, values, **kwargs):
        eos = []
        [eos.append(int(eo)) for eo in v if eo.isdigit() and eo not in eos]
        return eos
