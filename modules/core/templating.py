"""
Fates List Templating System
"""

import markdown

from .imports import *
from .permissions import is_staff


# Template class renderer
class templates():
    @staticmethod
    async def TemplateResponse(f, arg_dict: dict, *, context: dict = {}, not_error: bool = True, compact: bool = True):
        request = arg_dict["request"]
        worker_session = request.app.state.worker_session
        db = worker_session.postgres
        status = arg_dict.get("status_code")
        if "user_id" in request.session.keys():
            user_data = await db.fetchrow("SELECT state, user_css FROM users WHERE user_id = $1", int(request.session["user_id"]))
            state, arg_dict["user_css"] = user_data["state"], user_data["user_css"]
            if (state == enums.UserState.global_ban) and not_error:
                ban_type = enums.UserState(state).__doc__
                return await templates.e(request, f"You have been {ban_type} banned from Fates List<br/>", status_code = 403)
            if not compact:
                arg_dict["staff"] = (await is_staff(None, int(request.session["user_id"]), 2))[2]
            arg_dict["avatar"] = request.session.get("avatar")
            arg_dict["username"] = request.session.get("username")
            arg_dict["user_id"] = int(request.session.get("user_id"))
            if request.session.get("user_id"):
                arg_dict["user_token"] = await db.fetchval("SELECT api_token FROM users WHERE user_id = $1", arg_dict["user_id"]) 
            arg_dict["intl_text"] = intl_text # This comes from lynxfall.utils.string
            arg_dict["site_lang"] = request.session.get("site_lang", "default")
            arg_dict["scopes"] = request.session.get("scopes")
        else:
            arg_dict["staff"] = [False]
        arg_dict["site_url"] = site_url
        arg_dict["data"] = arg_dict.get("data")
        arg_dict["path"] = request.url.path
        arg_dict["enums"] = enums
        arg_dict["len"] = len
        arg_dict["ireplace"] = ireplace
        arg_dict["ireplacem"] = ireplacem
        arg_dict["human_format"] = human_format
        arg_dict["server_bot_invite"] = server_bot_invite

        base_context = {
            "user_id": str(arg_dict["user_id"]) if "user_id" in arg_dict.keys() else None,
            "user_token": arg_dict.get("user_token"),
            "site_lang": arg_dict.get("site_lang"),
            "logged_in": "user_id" in arg_dict.keys(),
            "index": "/",
            "type": "bot"
        }
        
        arg_dict["context"] = base_context | context
        arg_dict["md"] = lambda s: emd(markdown.markdown(s, extensions = md_extensions))        
        _templates = worker_session.templates
        
        if status is None:
            ret = _templates.TemplateResponse(f, arg_dict)
            
        else:
            ret = _templates.TemplateResponse(f, arg_dict, status_code = status)
            
        return ret

    @staticmethod
    async def error(f, arg_dict, status_code):
        arg_dict["status_code"] = status_code
        return await templates.TemplateResponse(f, arg_dict, not_error = False)

    @staticmethod
    async def e(request, reason: str, status_code: int = 404, *, main: Optional[str] = ""):
        return await templates.error("message.html", {"request": request, "message": main, "reason": reason, "retmain": True}, status_code)
