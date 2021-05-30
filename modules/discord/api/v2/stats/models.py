from pydantic import BaseModel
from typing import Optional

class BotListStats(BaseModel):
    uptime: float
    pid: int
    up: bool
    dup: bool
    bot_count: int
    bot_count_total: int
    workers: Optional[list] = None
