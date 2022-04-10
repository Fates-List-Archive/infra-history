import datetime
from typing import ForwardRef

from piccolo.columns.column_types import (UUID, Array, BigInt, Boolean, Float,
                                          ForeignKey, Integer, Secret, Text,
                                          Timestamptz, Varchar, Interval, Serial, JSONB)
from piccolo.columns.readable import Readable
from piccolo.table import Table
import uuid
from enum import Enum

from modules.models import enums

class LeaveOfAbsence(Table, tablename="leave_of_absence"):
    id = Serial(primary_key=True)
    user_id = BigInt(help_text="The user id of the user who is on leave. This is autofilled on submit")
    reason = Text(help_text="Reason for the leave of absence")
    estimated_time = Interval(help_text="Estimated time")
    start_date = Timestamptz(help_text="Start date", default=datetime.datetime.now())

class Vanity(Table, tablename="vanity"):
    vanity_url = Text(unique=True, required=True)
    type = Integer(choices = enums.Vanity)
    redirect = BigInt(primary_key=True)

class User(Table, tablename="users"):
    description = Text(default = "This user prefers to be an enigma")
    badges = Array(base_column = Text(), help_text = "Custom User Badges. The ones currently on profiles are special and manually handled without using this column.")
    username = Text()
    profile_css = Text(default = "")
    user_css = Text(default = "")
    state = Integer(default = 0, choices = enums.UserState)
    coins = Integer(default = 0)
    api_token = Text()

class UserBotLogs(Table, tablename="user_bot_logs"):
    user_id = ForeignKey(references=User, primary_key=True)
    bot_id = BigInt()
    action_time = Timestamptz(default=datetime.datetime.now())
    action = Integer(choices=enums.UserBotAction)
    context = Text()

class Bot(Table, tablename="bots"):
    bot_id = BigInt(primary_key=True)
    client_id = BigInt()
    username_cached = Text()
    verifier = BigInt(null=True)
    state = Integer(choices = enums.BotState, default = 1)
    description = Text()
    long_description_type = Integer(default = 0, choices = enums.LongDescType)
    long_description = Text()
    votes = BigInt(default = 0)
    guild_count = BigInt(default = 0)
    shard_count = BigInt(default = 0)
    shards = Array(base_column = Integer())
    user_count = BigInt(default = 0)
    last_stats_post = Timestamptz(default = datetime.datetime.now())
    created_at = Timestamptz(default = datetime.datetime.now())
    webhook_type = Integer(choices = enums.WebhookType)
    webhook = Text()
    webhook_secret = Text()
    bot_library = Text()
    css = Text(default = "")
    prefix = Varchar(length = 13)
    di_text = Text(help_text = "Discord Integration Text (unused)")
    website = Text()
    discord = Text()
    banner_card = Text()
    banner_page = Text()
    keep_banner_decor = Boolean(default = True)
    github = Text()
    donate = Text()
    privacy_policy = Text()
    nsfw = Boolean(default = False)
    api_token = Text()
    invite = Text()
    invite_amount = Integer(default = 0)
    features = Array(base_column = Text(), default = [])
    flags = Array(base_column = Integer(), default = [])
    uptime_checks_total = BigInt()
    uptime_checks_failed = BigInt()
    page_style = Integer(choices = enums.PageStyle)

class BotVotes(Table, tablename="user_vote_table"):
    user_id = BigInt(primary_key=True, help_text="The user id of the user who voted")
    bot_id = BigInt(null=False)
    expires_on = Timestamptz(default=datetime.datetime.now())

class BotPack(Table, tablename="bot_packs"):
    id = UUID(primary_key=True)
    icon = Text()
    banner = Text()
    name = Text()
    description = Text()
    owner = ForeignKey(references=User)
    bots = Array(base_column = BigInt())
    created_at = Timestamptz(default = datetime.datetime.now())

class BotCommand(Table, tablename="bot_commands"):
    id = UUID(primary_key=True)
    bot_id = ForeignKey(references=Bot)
    cmd_type = Integer(choices = enums.CommandType)
    groups = Array(base_column = Text())
    name = Text()
    vote_locked = Boolean(default = False)
    description = Text()
    args = Array(base_column = Text())
    examples = Array(base_column = Text())
    premium_only = Boolean(default = False)
    notes = Array(base_column = Text())
    doc_link = Text(help_text = "Link to documentation of command")


class BotTag(Table, tablename="bot_tags"):
    bot_id = ForeignKey(references=Bot)
    tag = Text(null = False)

class BotListTags(Table, tablename="bot_list_tags"):
    id = Text(null = False, unique=True, primary_key=True)
    icon = Text(null = False, unique=True)

class ServerTags(Table, tablename="server_tags"):
    # id TEXT NOT NULL UNIQUE, name TEXT NOT NULL UNIQUE, iconify_data TEXT NOT NULL, owner_guild BIGINT NOT NULL
    id = Text(null = False, unique=True, primary_key=True)
    name = Text(null = False, unique = True)
    iconify_data = Text(null = False)
    owner_guild = BigInt(null = False)

class Reviews(Table, tablename="reviews"):
    """Never ever make reviews on your own through this panel"""
    id = UUID(primary_key=True)
    target_type = Integer(choices=enums.ReviewType)
    target_id = BigInt()
    user_id = ForeignKey(references=User)
    star_rating = Float(help_text = "Amount of stars a bot has")
    review_text = Text(null=False)
    flagged = Boolean(default=False)
    epoch = Array(base_column = BigInt(), default=[])
    parent_id =  ForeignKey(references="Reviews")

    #@classmethod
    #def get_readable(cls):
    #    return Readable(template="%s", columns=[cls.name])
class ReviewVotes(Table, tablename="review_votes"):
    id = ForeignKey(references="Reviews")
    user_id = ForeignKey(references=User)
    upvote = Boolean(help_text="Whether the user upvoted or downvoted")

class _NotificationType(Enum):
    alert = "alert"

class Notifications(Table, tablename="lynx_notifications"):
    id = UUID(primary_key=True, default=uuid.uuid4)
    type = Text(choices=_NotificationType)
    message = Text(null=False)
    staff_only = Boolean(default=False, null = False)
    acked_users = Array(base_column = BigInt(), default=[])

class LynxRatings(Table, tablename="lynx_ratings"):
    id = UUID(primary_key=True, default=uuid.uuid4)
    feedback = Text(null=False)
    page = Text(null=False)
    username_cached = Text(null=False)
    user_id = ForeignKey(references=User)

class LynxSurveys(Table, tablename="lynx_surveys"):
    id = UUID(primary_key=True, default=uuid.uuid4)
    title = Text(null=False)
    questions = JSONB(null=False)
    created_at = Timestamptz(default=datetime.datetime.now())

class LynxSurveyResponses(Table, tablename="lynx_survey_responses"):
    id = UUID(primary_key=True, default=uuid.uuid4)
    survey_id = ForeignKey(references=LynxSurveys)
    questions = JSONB(null=False)
    answers = JSONB(null=False)
    username_cached = Text(null=False)
    user_id = ForeignKey(references=User)
