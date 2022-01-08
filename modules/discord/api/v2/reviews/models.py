import uuid
from typing import ForwardRef, List, Optional

from pydantic import BaseModel, validator

import modules.models.enums as enums

from ..base_models import APIResponse, BasePager, BaseUser


class BotReviewPartial(BaseModel):
    """Note that the reply and id fields are not honored in edit bot"""

    id: uuid.UUID | None = None
    review: str
    star_rating: float
    reply: bool | None = False

    @validator("reply")
    def id_or_no_reply(cls, v, values, **kwargs):
        if v and not id:
            raise ValueError("ID must be provided if reply is set")
        return v


class BotReviewPartialExt(BotReviewPartial):
    """Partial bot review with extended fields specific for adding reviews such as target_type and target_id"""

    target_type: enums.ReviewType
    target_id: str

    @validator("target_id")
    def validate_tgt_id(cls, v, values, **kwargs):
        if v.isdigit():
            return int(v)
        raise ValueError("Invalid target_id")


BotReviewList = ForwardRef("BotReviewList")


class BotReview(BaseModel):
    id: uuid.UUID
    reply: bool
    user_id: str
    star_rating: float
    review: str
    review_upvotes: list
    review_downvotes: list
    flagged: bool
    epoch: list
    time_past: str
    user: BaseUser
    replies: BotReviewList | None = []


class BotReviewList(BaseModel):
    """
    Represents a list of bot reviews on Fates List
    """

    __root__: list[BotReview]


class BotReviews(BaseModel):
    """Represents bot reviews and average stars of a bot on Fates List"""

    reviews: BotReviewList
    average_stars: float
    pager: BasePager


BotReview.update_forward_refs()
BotReviews.update_forward_refs()


class BotReviewVote(BaseModel):
    upvote: bool
