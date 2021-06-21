from pydantic import BaseModel, validator
import modules.models.enums as enums
from ..base_models import BaseUser, APIResponse, AccessToken
from typing import Optional, List, Union
import uuid

class Callback(BaseModel):
    key: str
    verify_key: str
    name: str
    url: str

class BaseLoginInfo(BaseModel):
    scopes: List[str]
    redirect: Optional[str] = "/"
      
class Login(BaseLoginInfo):
    """Code must be used normally. 
    Access token is only if bb_key matches and auth type must be temp_limited
    """
    code: str
    bb_key: Optional[str] = None
    auth_type: enums.AuthTypes
    access_token: Optional[str] = None
    
    @validator("access_token")
    def access_token_bb_check(cls, v, values, **kwargs):
        if not v:
            return v 
        if not secure_strcmp(values["bb_key"], bb_key):
            raise ValueError('Invalid BotBlock key')
        if values["auth_type"] != enums.AuthTypes.temp_limited:
            raise ValueError('Invalid auth type. BotBlock auth type must be temp_limited')
        
class LoginInfo(BaseLoginInfo):
    callback: Callback
 
class OAuthInfo(APIResponse):
    url: Optional[str] = "/"

class LoginBan(BaseModel):
    type: str
    desc: str

class LoginResponse(APIResponse):
    user: BaseUser = BaseUser(
        id = "0", 
        username = "Unknown", 
        avatar = "Unknown", 
        disc = "0000", 
        status = 0, 
        bot = False
    )
    ban: LoginBan = LoginBan(type = "Unknown", desc = "Unknown Ban Type")
    banned: bool = False
    token: str = None
    css: Union[str, None] = None
    state: enums.UserState = None
    js_allowed: bool = False
    access_token: AccessToken = AccessToken(access_token = "", refresh_token = "", expires_in = 0, current_time = 0)
    redirect: str = "/"
