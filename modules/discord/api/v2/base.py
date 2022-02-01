from modules.discord.api.v2.base_models import APIResponse

API_VERSION = 2 # API Version

responses = {
    400: {"model": APIResponse},
    404: {"model": APIResponse},
    422: {"model": APIResponse},
    403: {"model": APIResponse},
}