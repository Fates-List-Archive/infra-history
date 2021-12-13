from modules.core import *

from ..base import API_VERSION
from .models import APIResponse, BotResourcesGet, BotResource, IDResponse, enums, BotResources, BotResourceDelete

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/resources",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Custom Resources"],
)

@router.get(
    "/{target_id}", 
    response_model = List[dict],
    operation_id="get_resources"
)
async def get_resources(request:  Request, target_id: int, target_type: enums.ReviewType, filter: Optional[str] = None, lang: str = "default"):
    resources = await db.fetch("SELECT id, resource_title, resource_link, resource_description FROM resources WHERE target_id = $1 AND target_type = $2", target_id, target_type.value)
    if not resources:
        return abort(404)
    return resources

@router.post(
    "/{target_id}",
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=20, minutes=1),
                sub_limits = [Limit(times=5, seconds=15)]
            )
        ),
        Depends(bot_server_auth_check)
    ],
    operation_id="add_resources"
)
async def add_resources(request: Request, target_id: int, target_type: enums.ReviewType, res: BotResources):
    """
    Adds a resource to your bot/guild. If it already exists, this will delete and readd the resource so it can be used to edit already existing resources
    """
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
        await bot_add_event(target_id, enums.APIEvents.resource_add, {"user": None, "id": ids})
    return api_success(id = ids)

@router.delete(
    "/{target_id}", 
    response_model = APIResponse, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=20, minutes=1),
                sub_limits = [Limit(times=5, seconds=15)]
            )
        ), 
        Depends(bot_server_auth_check)
    ],
    operation_id="delete_resources"
)
async def delete_resources(request: Request, target_id: int, target_type: enums.ReviewType, resources: BotResourceDelete):
    """
    If ids/names is provided, all resources with said ids/names will be deleted (this can be used together). 
    If nuke is provided, then all resources will deleted. Ids/names and nuke cannot be used at the same time
    """
    if resources.nuke:
        await db.execute("DELETE FROM resources WHERE target_id = $1 AND target_type = $2", target_id, target_type)
        if target_type == enums.ReviewType.bot:
            await bot_add_event(bot_id, enums.APIEvents.resource_delete, {"user": None, "ids": [], "names": [], "nuke": True})
        return api_success()

    for id in resources.ids:
        await db.execute("DELETE FROM resources WHERE id = $1 AND target_id = $2 AND target_type = $3", id, target_id, target_type)
    for name in resources.names:
        await db.execute("DELETE FROM resources WHERE (resource_title = $1 OR resource_link = $1) AND target_id = $2 AND target_type = $3", name, target_id, target_type)

    if target_type == enums.ReviewType.bot:
        await bot_add_event(target_id, enums.APIEvents.resource_delete, {"user": None, "ids": resources.ids, "names": resources.names, "nuke": False})
    return api_success()
