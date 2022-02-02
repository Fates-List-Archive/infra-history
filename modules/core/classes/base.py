from aioredis import Connection
from pydantic import BaseModel
from modules.core.cache import get_any
from asyncpg import Pool

class DiscordUser():
    def __init__(self, *, id: int, worker_session):
        self.id = id
        self.worker_session = worker_session
        self.redis: Connection = worker_session.redis
        self.db: Pool = worker_session.postgres

    # TODO: Is this the best way to do this
    async def fetch(self):
        """Generic method to fetch a user"""
        return await get_any(self.id, worker_session=self.worker_session)
