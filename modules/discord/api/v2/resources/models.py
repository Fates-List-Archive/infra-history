import uuid
from typing import Dict, List, Optional

from pydantic import BaseModel, validator

import modules.models.enums as enums

from ..base_models import APIResponse, BaseUser, IDResponse


class BotResource(BaseModel):
    resource_title: str
    resource_link: str
    resource_description: str


class BotResourceWithId(BotResource):
    id: uuid.UUID


class BotResourcesGet(BaseModel):
    __root__: dict[str, list[BotResourceWithId]]


class BotResources(BaseModel):
    resources: list[BotResource]


class BotResourceDelete(BaseModel):
    ids: list[uuid.UUID] | None = None
    titles: list[str] | None = None
    nuke: bool | None = False

    @staticmethod
    @validator("nuke")
    def nuke_check(cls, v, values, **kwargs):
        if "ids" in values:
            if values["ids"] and v:
                raise ValueError(
                    "ids and nuke cannot be used at the same time!")
        if "titles" in values:
            if values["titles"] and v:
                raise ValueError(
                    "titles and nuke cannot be used at the same time!")
        return v
