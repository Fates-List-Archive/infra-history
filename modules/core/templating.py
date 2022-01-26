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
        status = arg_dict.get("status_code")
        arg_dict["site_lang"] = "en"
        arg_dict["site_url"] = site_url
        arg_dict["data"] = arg_dict.get("data")
        arg_dict["path"] = request.url.path
        arg_dict["enums"] = enums
        arg_dict["len"] = len
        arg_dict["ireplace"] = ireplace
        arg_dict["ireplacem"] = ireplacem
        arg_dict["intl_text"] = intl_text # This comes from lynxfall.utils.string
        arg_dict["human_format"] = human_format # This comes from lynxfall.utils.string
        base_context = {
            "site_lang": arg_dict.get("site_lang"),
            "logged_in": True,
            "index": "/",
            "type": "bot",
            "site_url": site_url
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
        return api_error("Unknown error")

    @staticmethod
    async def e(request, reason: str, status_code: int = 404, *, main: Optional[str] = ""):
        return api_error(f"{main}: {reason}", status_code=status_code)
