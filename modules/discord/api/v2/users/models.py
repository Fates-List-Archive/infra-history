import uuid
from typing import List, Optional

from pydantic import BaseModel, validator

from modules.models import enums

from ..base_models import APIResponse, BaseUser, BotPackPartial, IDResponse


class UpdateUserPreferences(BaseModel):
    """Setting field to null and/or omitting it means no change to said field."""

    description: str | None = None
    profile_css: str | None = None
    user_css: str | None = None
    site_lang: enums.SiteLang | None = None
    vote_reminder_channel: str | None = None

    @validator("vote_reminder_channel")
    def channel_id_validator(cls, v):
        if v and not v.isdigit():
            raise ValueError("Invalid channel ID.")
        return v


class UpdateVoteReminders(BaseModel):
    mode: enums.VoteReminderMode
    bot_id: str

    @validator("bot_id")
    def bot_id_validator(cls, v):
        if not v.isdigit():
            raise ValueError("Invalid bot ID.")
        return v

class BotMeta(BaseModel):
    """
    Notes:

    - extra_owners must be a list of strings where the strings can be made a integer
    """
    client_id: str | None = None
    prefix: str | None = None
    library: str
    invite: str | None = "P:0"
    website: str | None = None
    description: str
    banner_card: str | None = None
    banner_page: str | None = None
    keep_banner_decor: bool
    extra_owners: list[str]  # List of strings that can be turned into a integer
    support: str | None = None
    long_description: str
    css: str | None = None
    long_description_type: enums.LongDescType
    page_style: enums.PageStyle | None = enums.PageStyle.tabs
    nsfw: bool
    donate: str | None = None
    privacy_policy: str | None = None
    github: str | None = None
    webhook_type: int | None = 0
    webhook: str | None = None
    webhook_secret: str | None = None
    vanity: str
    features: list[str] | None = []
    tags: list[str]
    system_bot: bool | None = False

    @validator("extra_owners")
    def extra_owner_converter(cls, v, values, **kwargs):
        eos = []
        [eos.append(int(eo.replace(" ", ""))) for eo in v if eo.replace(" ", "").isdigit() and eo.replace(" ", "") not in eos]
        return eos


class OwnershipTransfer(BaseModel):
    new_owner: str

    @validator("new_owner")
    def new_owner_validator(cls, v, values, **kwargs):
        try:
            new_owner = str(v)
        except:
            raise ValueError("Invalid new owner")
        return new_owner


class BotAppeal(BaseModel):
    appeal: str

class BotVoteCheck(BaseModel):
    """vts = Vote Timestamps"""
    votes: int
    voted: bool
    vote_right_now: bool | None = None
    vote_epoch: int | None = None
    time_to_vote: int | None = None
    vts: list | None = None
