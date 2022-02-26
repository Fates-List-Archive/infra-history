from modules.core import *

from ..base import API_VERSION
from .models import APIResponse, BotCommandsGet, BotCommand, IDResponse, enums, BotCommands, BotCommandDelete

router = APIRouter(
    prefix = f"/bots",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Commands"],
)

@router.post(
    "/{bot_id}/commands",
    dependencies=[
        Depends(bot_auth_check)
    ],
    operation_id="add_commands"
)
async def add_commands(request: Request, bot_id: int, commands: BotCommands):
    """
    Adds a command to your bot. If it already exists, this will delete and readd the command so it can be used to edit already existing commands
    """
    db = request.app.worker_session.postgres
    redis = request.app.worker_session.redis
    ids = []
    for command in commands.commands:
        command.cmd_groups = [c.lower() for c in command.cmd_groups]
        check = await db.fetchval("SELECT COUNT(1) FROM bot_commands WHERE cmd_name = $1 AND bot_id = $2", command.cmd_name, bot_id)
        if check:
            await db.execute("DELETE FROM bot_commands WHERE cmd_name = $1 AND bot_id = $2", command.cmd_name, bot_id)
        id = uuid.uuid4()
        await db.execute("INSERT INTO bot_commands (id, bot_id, cmd_groups, cmd_type, cmd_name, description, args, examples, premium_only, notes, doc_link, vote_locked) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)", id, bot_id, command.cmd_groups, command.cmd_type, command.cmd_name, command.description, command.args, command.examples, command.premium_only, command.notes, command.doc_link, command.vote_locked)
        ids.append(str(id))
    await add_ws_event(
        redis,
        bot_id,
        {
            "m": {
                "e": enums.APIEvents.command_add, 
            },
            "ctx": {
                "id": ids
            }
        }
    )
    return api_success(id = ids)

@router.delete(
    "/{bot_id}/commands", 
    response_model = APIResponse, 
    dependencies=[
        Depends(bot_auth_check)
    ],
    operation_id="delete_commands"
)
async def delete_commands(request: Request, bot_id: int, commands: BotCommandDelete):
    """
    If ids/names is provided, all commands with said ids/names will be deleted (this can be used together). 
    If nuke is provided, then all commands will deleted. Ids/names and nuke cannot be used at the same time
    """
    db = request.app.worker_session.postgres
    redis = request.app.worker_session.redis
    if commands.nuke:
        await db.execute("DELETE FROM bot_commands WHERE bot_id = $1", bot_id)
        await add_ws_event(
            redis,
            bot_id, 
            {
                "m": {
                    "e": enums.APIEvents.command_delete, 
                },
                "ctx": {
                    "nuke": True
                }
            }
        )
        return api_success()

    for id in commands.ids:
        await db.execute("DELETE FROM bot_commands WHERE id = $1 AND bot_id = $2", id, bot_id)
    for name in commands.names:
        await db.execute("DELETE FROM bot_commands WHERE cmd_name = $1 AND bot_id = $2", name, bot_id)
    await add_ws_event(
        redis,
        bot_id, 
        {
            "m": {
                "e": enums.APIEvents.command_delete, 
            },
            "ctx": {
                "ids": commands.ids,
                "names": commands.names, 
                "nuke": False
            }
        }
    )
    return api_success()
