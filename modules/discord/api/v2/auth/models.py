import uuid
from typing import List, Optional, Union

from pydantic import BaseModel, validator

import modules.models.enums as enums

from ..base_models import APIResponse, BaseUser
from config import auth_namespaces

class Login(BaseModel):
    code: str
    scopes: list[str]
        
class LoginInfo(BaseModel):
    scopes: list[str]
 
class OAuthInfo(APIResponse):
    url: str | None = "/"
    state: str

class LoginBan(BaseModel):
    type: str
    desc: str

class LoginResponse(APIResponse):
    ban: LoginBan = LoginBan(type = "Unknown", desc = "Unknown Ban Type")
    banned: bool = False
