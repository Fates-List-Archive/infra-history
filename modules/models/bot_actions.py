from modules.deps import *
def form_body(cls):
    cls.__signature__ = cls.__signature__.replace(
        parameters=[
            arg.replace(default=FForm(""))
            for arg in cls.__signature__.parameters.values()
        ]
    )
    return cls

class BotMeta(BaseModel):
    prefix: str
    library: str
    invite: str
    website: Optional[str] = ""
    description: str
    banner: Optional[str] = ""
    extra_owners: list
    support: Optional[str] = ""
    long_description: str
    css: Optional[str] = ""
    html_long_description: Optional[bool] = True
    donate: Optional[str] = ""
    github: Optional[str] = ""
    webhook_type: Optional[str] = ""
    webhook: Optional[str] = ""
    vanity: Optional[str] = ""

class BaseForm(BotMeta):
    custom_prefix: str = FForm("on")
    open_source: str = FForm("on")
    tags: str = FForm("")
    extra_owners: str = FForm("")

@form_body
class BotAddForm(BaseForm):
    bot_id: int

@form_body
class BotEditForm(BaseForm):
    pass

class BotAPIMeta(BotMeta):
    """
        OAuth access token is not *required* but is recommended for security
    """
    features: Optional[list] = []
    tags: list
    oauth_access_token: Optional[str] = None # Not passing this will disable oauth check
    oauth_enforced: Optional[bool] = True # NOT RECOMMENDED, BUT ITS THERE
    owner: str

class BotAdd(BotAPIMeta):
    pass

class BotEdit(BotAPIMeta):
    pass
