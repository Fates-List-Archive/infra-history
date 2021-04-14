"""
Fates List Error System
"""

from .imports import *
from .templating import *

@jit(forceobj=True)
def etrace(ex):
    trace = []
    tb = ex.__traceback__
    while tb is not None:
        trace.append({
            "filename": tb.tb_frame.f_code.co_filename,
            "name": tb.tb_frame.f_code.co_name,
            "lineno": tb.tb_lineno
        })
        tb = tb.tb_next
    return str({
        'type': type(ex).__name__,
        'message': str(ex),
        'trace': trace
    })

class WebError():
    @staticmethod
    async def log(request, exc, error_id, curr_time):
        traceback = exc.__traceback__ # Get traceback from exception
        site_errors = client.get_channel(site_errors_channel) # Get site errors channel
        if site_errors is None: # If this is None, config is wrong or we arent connected to Discord yet, in this case, raise traceback
            raise traceback
        try:
            fl_info = f"Error ID: {error_id}\n\nMinimal output\n\n" # Initial header
            while traceback is not None: # Loop through traceback recursively
                fl_info += f"{traceback.tb_frame.f_code.co_filename}: {traceback.tb_lineno}\n" # tb_frame.f_code.co_filename is the filename and tb_lineno is line number
                traceback = traceback.tb_next # Get the next part of traceback 
            try:
                fl_info += f"\n\nExtended output\n\n{etrace(exc)}" # Extended output
            except:
                fl_info += f"\n\nExtended output\n\nNo extended output could be logged..." # Could not log anything
        except:
            pass
        await site_errors.send(f"500 (Internal Server Error) at {str(request.url).replace('https://', '')}\n\n**Error**: {exc}\n**Type**: {type(exc)}\n**Data**: File will be uploaded below if we didn't run into errors collecting logging information\n\n**Error ID**: {error_id}\n**Time When Error Happened**: {curr_time}") # Send the 500 message to site errors
        fl_file = discord.File(io.BytesIO(bytes(fl_info, 'utf-8')), f'{error_id}.txt') # Create a file on discord
        if fl_file is not None:
            await site_errors.send(file=fl_file) # Send it
        else:
            await site_errors.send("No extra information could be logged and/or send right now") # Could not send it

    @staticmethod
    async def error_handler(request, exc):
        error_id = str(uuid.uuid4()) # Create a error id
        curr_time = str(datetime.datetime.now()) # Get time error happened
        try:
            status_code = exc.status_code # Check for 422 and 500 using status code presence
        except: # 500 and 422 do not have status code
            if type(exc) == RequestValidationError: # This is when incorrect arguments were passed (422)
                exc.status_code = 422
            else: # Internal Server Error (500)
                exc.status_code = 500
        path = str(request.url.path)
        match exc.status_code: # Python 3.10 introduced pattern matching, use that to check for http code
            case 401:
                return ORJSONResponse({"done": False, "reason": "Unauthorized", "code": 9999}, status_code = exc.status_code)
            case 500:
                asyncio.create_task(WebError.log(request, exc, error_id, curr_time)) # Try and log what happened
                if str(request.url.path).startswith("/api"):
                    return ORJSONResponse({"done": False, "reason": f"Internal Server Error\nError ID: {error_id}\nTime when error happened: {curr_time}\nOur developers have been notified and are looking into it."}, status_code = exc.status_code)
                return HTMLResponse(f"<strong>500 Internal Server Error</strong><br/>Fates List had a slight issue and our developers and looking into what happened<br/><br/>Error ID: {error_id}<br/>Time When Error Happened: {curr_time}\nPlease check our support server at <a href='{support_url}'>{support_url}</a> for more information", status_code=500) # Send 500 error to user with aupport server
            case 404: 
                if path.startswith("/bot"): # Bot 404
                    msg = "Bot Not Found"
                    code = 404
                elif path.startswith("/profile"): # Profile 404
                    msg = "Profile Not Found"
                    code = 404
                else: # Regular 404
                    msg = "404\nNot Found"
                    code = 404
            case 401:
                msg = "401\nNot Authorized"
                code = 401
            case 403:
                msg = "403\nForbidden"
                code = 403
            case 422:
                if path.startswith("/bot"): # Bot 422 which is actually 404 to us
                    msg = "Bot Not Found"
                    code = 404
                elif path.startswith("/profile"): # Profile 422 which is actually 404 to us
                    msg = "Profile Not Found"
                    code = 404
                else:
                    msg = "Invalid Data Provided<br/>" + str(exc) # Regular 422
                    code = 422
            case _:
                msg = "Unknown Error" # Unknown error, no case for it yet
                code = 400

        json = path.startswith("/api") # Check if api route, return JSON if it is
        if json: # If api route, return JSON
            if exc.status_code != 422:
                return await http_exception_handler(request, exc) # 422 needs special request handler, all others can use this
            else:
                return await request_validation_exception_handler(request, exc) # Other codes can use normal one, 422 needs this
        return await templates.e(request, msg, code) # Otherwise return error