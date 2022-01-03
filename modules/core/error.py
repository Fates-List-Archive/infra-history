import io
import time
import traceback
import uuid
from http import HTTPStatus

from .imports import *
from .ipc import redis_ipc_new
from .templating import *


def etrace(ex):
    try:
        return "".join(traceback.format_exception(ex)) # COMPAT: Python 3.10 only
    except:
        return str(ex)

class WebError():
    @staticmethod
    async def log(request, exc, error_id, curr_time):
        try:
            fl_info = f"Error ID: {error_id}\n\n" # Initial header
            fl_info += etrace(exc)
        
        except Exception:
            fl_info = "No exception could be logged"
        
        url = str(request.url).replace('https://', '').replace("http://localhost:1843", "fateslist.xyz")
        msg = inspect.cleandoc(f"""500 (Internal Server Error) at {url}

        **Error**: {exc}

        **Error ID**: {error_id}

        **Time When Error Happened**: {curr_time}""") 
         
        await redis_ipc_new(redis_db, "SENDMSG", msg = {"content": msg, "file_name": f"{error_id}.txt", "file_content": fl_info, "channel_id": str(site_errors_channel)})

        # Reraise exception
        try:
            raise exc
        except:
            logger.exception("Site Error Occurred")


    @staticmethod
    async def error_handler(request, exc, log: bool = True):
        error_id = str(uuid.uuid4())
        curr_time = time.time()

        try:
            # All status codes other than 500 and 422
            status_code = exc.status_code 
        
        except Exception: 
            # 500 and 422 do not have status codes and need special handling
            if isinstance(exc, RequestValidationError): 
                status_code = 422
            
            else: 
                status_code = 500
        
        path = str(request.url.path)
        
        code_str = HTTPStatus(status_code).phrase
        api = path.startswith("/api/")
        if status_code == 500:
            # Log the error
            asyncio.create_task(WebError.log(request, exc, error_id, curr_time)) 
            
            if api:
                return api_error(
                    "Internal Server Error", 
                    error_id=error_id, 
                    status_code=500,
                    traceback=etrace(exc),
                    headers={"FL-Error-ID": error_id}
                )
           
            try:
                tb_full = "".join(traceback.format_exception(exc))
            except Exception:
                tb_full = "".join(traceback.format_tb(exc))

            errmsg = inspect.cleandoc(f"""
            <body style="background: #D3D3D3">
                <strong>Fates List had a slight issue and our developers and looking into what happened</strong><br/><br/>
                
                Error ID: {error_id}<br/><br/>

                Please check our support server at <a href='{support_url}'>{support_url}</a> for more information<br/><br/>

                Please send the below traceback if asked:<br/><br/>

                <pre>{tb_full.replace("<", "&lt;").replace(">", "&gt;")}</pre>

                Time When Error Happened: {curr_time}<br/>
            </body>
            """)

            return HTMLResponse(errmsg, status_code=status_code, headers={"FL-Error-ID": error_id})

        if not api:
            # Special error messages (some with custom-set status code)
            if status_code == 404: 
                if path.startswith("/bot"):
                    code_str = "Bot Not Found"
        
                elif path.startswith("/profile"): 
                    code_str = "Profile Not Found"
            
            elif status_code == 422:
                if path.startswith("/bot"): 
                    code_str = "Bot Not Found"
                    status_code = 404
            
                elif path.startswith("/profile"): 
                    code_str = "Profile Not Found"
                    status_code = 404
            
            return await templates.e(request, code_str, status_code)

        # API route handling
        if status_code != 422:
            # Normal handling
            return ORJSONResponse({"done": False, "reason": exc.detail}, status_code=status_code)
        else:
            errors = exc.errors()
            errors_fixed = []
            for error in errors:
                if error["type"] == "type_error.enum":
                    ev = [{"name": type(enum).__name__, "accepted": enum.value, "doc": enum.__doc__} for enum in error["ctx"]["enum_values"]]
                    error["ctx"]["enum"] = ev
                    del error["ctx"]["enum_values"]
                errors_fixed.append(error)
            return ORJSONResponse({"done": False, "reason": "Invalid fields present", "ctx": errors_fixed}, status_code=422)
