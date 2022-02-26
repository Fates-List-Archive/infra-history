from modules.core import *

from ..base import API_VERSION
from .models import APIResponse, BotResourcesGet, BotResource, IDResponse, enums, BotResources, BotResourceDelete

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/resources",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Custom Resources"],
)

@router.post(
    "/{target_id}",
    dependencies=[
        Depends(bot_server_auth_check)
    ],
    operation_id="add_resources"
)
async def add_resources(request: Request, target_id: int, target_type: enums.ReviewType, res: BotResources):
    """
    Adds a resource to your bot/guild. If it already exists, this will delete and readd the resource so it can be used to edit already existing resources
    """
    db = request.app.worker_session.postgres
    redis = request.app.worker_session.redis
    await redis.delete(f"botpagecache:{target_id}")
    ids = []
    for resource in res.resources:
        if not resource.resource_link.startswith("https://"):
            return api_error("All resource links must start with https://")
        check = await db.fetchval("SELECT COUNT(1) FROM resources WHERE (resource_title = $1 OR resource_link = $2) AND target_id = $3 AND target_type = $4", resource.resource_title, resource.resource_link, target_id, target_type.value)
        if check:
            await db.execute("DELETE FROM resources WHERE (resource_title = $1 OR resource_link = $2) AND target_id = $3 AND target_type = $4", resource.resource_title, resource.resource_link, target_id, target_type.value)
        id = uuid.uuid4()
        await db.execute("INSERT INTO resources (id, target_id, target_type, resource_title, resource_description, resource_link) VALUES ($1, $2, $3, $4, $5, $6)", id, target_id, target_type.value, resource.resource_title, resource.resource_description, resource.resource_link)
        ids.append(str(id))
    if target_type == enums.ReviewType.bot:
        await bot_add_event(redis, target_id, enums.APIEvents.resource_add, {"user": None, "id": ids})
    cachename = target_type.name.lower()
    await redis.delete(f"{cachename}cache-{target_id}-True")
    await redis.delete(f"{cachename}cache-{target_id}-False")
    return api_success(id = ids)

@router.delete(
    "/{target_id}", 
    response_model = APIResponse, 
    dependencies=[
        Depends(bot_server_auth_check)
    ],
    operation_id="delete_resources"
)
async def delete_resources(request: Request, target_id: int, target_type: enums.ReviewType, resources: BotResourceDelete):
    """
    If ids/names is provided, all resources with said ids/names will be deleted (this can be used together). 
    If nuke is provided, then all resources will deleted. Ids/names and nuke cannot be used at the same time
    """
    db = request.app.worker_session.postgres
    redis = request.app.worker_session.redis
    await redis.delete(f"botpagecache:{target_id}")
    if resources.nuke:
        await db.execute("DELETE FROM resources WHERE target_id = $1 AND target_type = $2", target_id, target_type)
        if target_type == enums.ReviewType.bot:
            await bot_add_event(redis, target_id, enums.APIEvents.resource_delete, {"user": None, "ids": [], "names": [], "nuke": True})
        return api_success()

    for id in resources.ids:
        await db.execute("DELETE FROM resources WHERE id = $1 AND target_id = $2 AND target_type = $3", id, target_id, target_type)
    for name in resources.names:
        await db.execute("DELETE FROM resources WHERE (resource_title = $1 OR resource_link = $1) AND target_id = $2 AND target_type = $3", name, target_id, target_type)

    if target_type == enums.ReviewType.bot:
        await bot_add_event(redis, target_id, enums.APIEvents.resource_delete, {"user": None, "ids": resources.ids, "names": resources.names, "nuke": False})
    cachename = target_type.name.lower()
    await redis.delete(f"{cachename}cache-{target_id}-True")
    await redis.delete(f"{cachename}cache-{target_id}-False")
    return api_success()
