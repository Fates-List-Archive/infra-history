import uuid
from typing import Dict, ForwardRef, List, Optional

from aenum import Enum, IntEnum
from pydantic import BaseModel

from modules.models.ula import *


class WidgetFormat(Enum):
    _init_ = "value __doc__"
    json = "json", "JSON Widget"
    html = "html", "HTML Widget"
    png = "png", "Widget (as png image)"
    webp = "webp", "Widget (as webp image)"

class PromotionType(IntEnum):
    _init_ = 'value __doc__'
    announcement = 0, "Announcement"
    promotion = 1, "Promotion"
    generic = 2, "Generic"
        
class CooldownBucket(Enum):
    requeue = 60*0.2
    ban = 60*0.3
    transfer = 60*0.5
    reset = 60*1
    lock = 60*2
    delete = 60*3.5

class BotAdminOp(Enum):
    """Handles bot admin operations"""
    _init_ = 'value __doc__ __perm__ __reason_needed__ __recursive__ __cooldown__'
    requeue = "REQUEUE", "Requeue Bot", 3, True, False, CooldownBucket.requeue
    claim = "CLAIM", "Claim Bot", 2, False, False, None
    unclaim = "UNCLAIM", "Unclaim Bot", 2, False, False, None
    ban = "BAN", "Ban Bot", 3, True, False, CooldownBucket.ban
    unban = "UNBAN", "Unban Bot", 3, True , False, CooldownBucket.ban
    certify = "CERTIFY", "Certify Bot", 5, False, False, None
    uncertify = "UNCERTTIFY", "Uncertify Bot", 5, True, False, None
    approve = "APPROVE", "Approve Bot", 2, True, False, None
    deny = "DENY", "Deny Bot", 2, True, False, None
    unverify = "UNVERIFY", "Unverify Bot", 3, True, False, CooldownBucket.ban
    reset_votes = "RESETVOTES", "Reset All Votes", (5, 7), True, True, CooldownBucket.reset
    staff_lock = "STAFFLOCK", "Staff Lock Bot", 4, True, False, None
    staff_unlock = "STAFFUNLOCK", "Staff Unlock Bot", 4, True, False, CooldownBucket.lock

    # TODO: To be implemented in go (or as an api, api seems better)
    bot_lock = "BLOCK", "Bot Lock", 0, False, False, None
    bot_unlock = "BUNLOCK", "Bot Unlock", 4, False, False, CooldownBucket.lock

class BotFlag(IntEnum):
    _init_ = 'value __doc__'
    unlocked = 0, "Bot unlocked for editing"
    edit_locked = 1, "Bot locked for editing"
    staff_locked = 2, "Bot locked by staff"
    stats_locked = 3, "Stats locked"
    vote_locked = 4, "Vote locked"
    system = 5, "System bot"

class UserState(IntEnum):
    _init_ = 'value __doc__ __sitelock__'
    normal = 0, "Normal (No Ban)", False
    global_ban = 1, "Global Ban", True
    profile_edit_ban = 2, "Profile Edit Ban", False
    ddr_ban = 3, "Data Deletion Request Ban", True
    api_ban = 4, "Full API Ban", False

class WebhookType(IntEnum):
    _init_ = 'value __doc__'
    vote = 0, "Vote Webhook"
    discord = 1, "Discord Integration"
    fc = 2, "Fates Client (deprecated)"

class Status(IntEnum):
    """Status object (See https://docs.fateslist.xyz/basics/basic-structures#status for more information)"""
    _init_ = 'value __doc__'
    unknown = 0, "Unknown"
    online = 1, "Online"
    offline = 2, "Offline"
    idle = 3, "Idle"
    dnd = 4, "Do Not Disturb"

class BaseUser(BaseModel):
    """
    Represents a base user class on Fates List.
    """
    id: str
    username: str
    avatar: str
    disc: str
    status: Status
    bot: bool
    
class BotState(IntEnum):
    _init_ = 'value __doc__'
    approved = 0, "Verified"
    pending = 1, "Pending Verification"
    denied = 2, "Denied"
    hidden = 3, "Hidden"
    banned = 4, "Banned"
    under_review = 5, "Under Review"
    certified = 6, "Certified"
    archived = 7, "Archived"
    private_viewable = 8, "Private, but viewable with link (server only)"
    private_staff_only = 9, "Private, only staff may join (server only)"

class UserBotAction(IntEnum):
    _init_ = "value __doc__"
    approve = 0, "Approve"
    deny = 1, "Deny"
    certify = 2, "Certify"
    ban = 3, "Ban"
    claim = 4, "Claim"
    unclaim = 5, "Unclaim"

class LongDescType(IntEnum):
    _init_ = 'value __doc__'
    html = 0, "HTML/Raw Description"
    markdown_pymarkdown = 1, "Markdown using Python Markdown"
    markdown_marked = 2, "Markdown using JavaScript Marked"

class Vanity(IntEnum):
    _init_ = "value __doc__"
    server = 0, "Server"
    bot = 1, "Bot"
    profile = 2, "Profile"

class SearchType(Enum):
    _init_ = "value __doc__"
    bot = "bot", "Bot"
    server = "server", "Server"
    profile = "profile", "Profile"

class CommandType(IntEnum):
    """
    0 - Regular (Prefix) Command

    1 - Slash Command (Guild)
    
    2 - Slash Command (Global)
    """
    _init_ = "value __doc__"
    regular = 0, "Regular Command"
    guild_slash = 1, "Slash Command (guild)"
    global_slash = 2, "Slash Command (global)"

class APIEvents(IntEnum):
    """May or may not be in numeric order"""
    _init_ = "value __doc__"
    bot_vote = 0, "Vote Bot Event"
    bot_add = 1, "Bot Add Event"
    bot_edit = 2, "Bot Edit Event"
    bot_delete = 3, "Bot Delete Event"
    bot_claim = 4, "Bot Claim Event"
    bot_approve = 5, "Bot Approve Event"
    bot_deny = 6, "Bot Deny Event"
    bot_ban = 7, "Bot Ban Event"
    bot_unban = 8, "Bot Unban Event"
    bot_requeue = 9, "Bot Requeue Event"
    bot_certify = 10, "Bot Certify Event"
    bot_uncertify = 11, "Bot Uncertify Event"
    bot_transfer = 12, "Bot Ownership Transfer Event"
    bot_hide = 13, "Bot Hide Event" # Whenever someone makes their bot hidden
    bot_archive = 14, "Bot Archive Event" # When someone archives their bot
    bot_unverify = 15, "Bot Unverify Event"
    bot_view = 16, "Bot View Event (Websocket only)" # WS only
    bot_invite = 17, "Bot Invite Event (Websocket only)" # WS only
    bot_unclaim = 18, "Bot Unclaim Event"
    bot_root_update = 19, "Bot Root State Update Event" # Whenever a head admin+ performs a Root State Update on a bot
    bot_vote_reset = 20, "Bot Votes Reset Event" # Whenever all votes for a particular bot either to prevent abuse or otherwise is reset
    bot_vote_reset_all = 21, "Bot Votes Reset All Event" # Whenever all votes are reset, this is usually every month but may not be
    bot_lock = 22, "Bot Lock Event"
    bot_unlock = 23, "Bot Unlock Event"
    review_vote = 30, "Review Vote Event"
    review_add = 31, "Bot Review Add Event"
    review_edit = 32, "Bot Review Edit Event"
    review_delete = 33, "Bot Review Delete Event"
    resource_add = 40, "Bot Resource Add Event"
    resource_delete = 41, "Bot Resource Delete Event"
    command_add = 50, "Bot Command Add Event"
    command_delete = 51, "Bot Command Delete Event"
    server_view = 70, "Server View Event"
    server_vote = 71, "Server Vote Event"
    server_invite = 72, "Server Invite Event"
    staff_lock = 80, "Staff Lock"
    staff_unlock = 81, "Staff Unlock"

class ReviewType(IntEnum):
    _init_ = "value __doc__"
    bot = 0, "Bot"
    server = 1, "Server"
