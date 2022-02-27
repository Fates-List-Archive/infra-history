from modules.core import *
from lynxfall.utils.string import human_format
from lynxfall.utils.fastapi import api_error, abort
from fastapi.responses import PlainTextResponse, StreamingResponse
from PIL import Image, ImageDraw, ImageFont
import io, textwrap, aiofiles
from starlette.concurrency import run_in_threadpool
from math import floor
from jinja2 import Environment, BaseLoader, select_autoescape
from fastapi import APIRouter, Request, Response, BackgroundTasks

from ..base import API_VERSION

router = APIRouter(
    include_in_schema = True,
)

from colour import Color

# Convert hexcode to rgb for pillow
def hex_to_rgb(value):
    value = value.lstrip('H')
    lv = len(value)
    return tuple(int(value[i:i+lv//3], 16) for i in range(0, lv, lv//3))

# Widget template
widgets_html_template = """
<head>
    <link href="https://fonts.googleapis.com/css2?family=Lexend+Deca&display=swap" rel="stylesheet">
    <script src="https://code.iconify.design/1/1.0.7/iconify.min.js"></script>
    <style>h5,div,span,p{font-family:'Lexend Deca',sans-serif;}</style>
</head>
<a href="https://fateslist.xyz/{{type}}/{{id}}">
    <div style="display:inline-block;background:{{bgcolor.replace('H', '#', 1) or '#111112'}};width:300px;height:175px;">
        <div style="margin-bottom:2px;">
            <div style="display:block;">
                <h5 style="color:white;margin-left:7px;margin-top:2px;"><strong>{{user.username}}</strong></h5>
                <img loading="lazy" src="{{user.avatar}}" style="border-radius:50px 50px 50px 50px;margin: 0 3px auto;text-align:center;width:100px;height:100px;display:inline-flex;float:left">
            </div>
            <div style="margin-left:10px;">
                <p style="color:{{textcolor.replace('H', '#', 1) or 'white'}};"><span class="iconify" data-icon="fa-solid:server"></span><span style="margin-left:5px;">{{human_format(bot.guild_count)}}</span><br/></p>
                <p style="color:{{textcolor.replace('H', '#', 1) or 'white'}};"><span class="iconify" data-icon="fa-solid:thumbs-up"></span><span style="margin-left:5px;">{{human_format(bot.votes)}}</span></p>
            </div>
        </div><br/>
        <p style="padding:3px;color:white;opacity:0.98;margin-top:2px;">Fates List</p>
    </div>
</a>
"""

env = Environment(
    loader=BaseLoader,
    autoescape=select_autoescape(),
    enable_async=True,
).from_string(widgets_html_template.replace("\n", "").replace("  ", ""), globals={"human_format": human_format})

def is_color_like(c):
    try:
        # Converting 'deep sky blue' to 'deepskyblue'
        color = c.replace(" ", "")
        Color(color)
        # if everything goes fine then return True
        return True
    except ValueError: # The color code was not found
        return False

@router.get("/{target_id}", operation_id="get_widget")
async def get_widget(
    request: Request, 
    response: Response,
    bt: BackgroundTasks, 
    target_id: int, 
    target_type: enums.WidgetType, 
    format: enums.WidgetFormat,
    bgcolor: str  = 'black', 
    textcolor: str ='white', 
    no_cache: Optional[bool] = False, 
    cd: Optional[str] = None, 
    desc_length: int = 25
):
    """
    Returns a widget

    **For colors (bgcolor, textcolor), use H for html hex instead of #.\nExample: H123456**

    - cd - A custom description you wish to set for the widget

    - desc_length - Set this to anything less than 0 to try and use full length (may 500), otherwise this sets the length of description to use.

    **Using 0 for desc_length will disable description**

    no_cache - If this is set to true, cache will not be used but will still be updated. If using cd, set this option to true and cache the image yourself
    Note that no_cache is slow and may lead to ratelimits and/or your got being banned if used excessively
    """
    if not bgcolor:
        bgcolor = "black"
    elif not textcolor:
        textcolor = "black"

    # HTML shouldn't have any changes to bgcolor
    if format != enums.WidgetFormat.html:
        if bgcolor.startswith("H"):
            # Hex code starting with H, make it rgb
            bgcolor = hex_to_rgb(bgcolor)
        else:
            # Converting 'deep sky blue' to 'deepskyblue'
            if not is_color_like(str(bgcolor)):
                return api_error("Invalid bgcolor")
            if isinstance(bgcolor, str):
                bgcolor=bgcolor.split('.')[0]
                bgcolor = floor(int(bgcolor)) if bgcolor.isdigit() or bgcolor.isdecimal() else bgcolor
        
        # HTML shouldn't have any changes to textcolor
        if textcolor.startswith("H"):
            textcolor = hex_to_rgb(textcolor)
        else:
            if not is_color_like(str(textcolor)):
                return api_error("Invalid textcolor")
            if isinstance(textcolor, str):
                textcolor=textcolor.split('.')[0]
                textcolor = floor(int(textcolor)) if textcolor.isdigit() or textcolor.isdecimal() else textcolor
    
    cache_key = f"widget-{target_id}-{target_type}-{format.name}-{textcolor}-{bgcolor}-{desc_length}"
    response.headers["ETag"] = f"W/{cache_key}"

    worker_session = request.app.state.worker_session
    db = worker_session.postgres
    redis = worker_session.redis
   
    if target_type == enums.WidgetType.bot:
        col = "bot_id"
        table = "bots"
        event = enums.APIEvents.bot_view
        _type = "bot"
    else:
        col = "guild_id"
        table = "servers"
        event = enums.APIEvents.server_view
        _type = "server"

    bot = await db.fetchrow(f"SELECT guild_count, votes, description FROM {table} WHERE {col} = $1", target_id)
    if not bot:
        return abort(404)
    
    bot = dict(bot)
    
    #bt.add_task(add_ws_event, redis, target_id, {"m": {"e": event}, "ctx": {"user": request.session.get('user_id'), "widget": True}}, type=_type)
    if target_type == enums.WidgetType.bot:
        data = {"bot": bot, "user": await get_bot(target_id, worker_session = request.app.state.worker_session)}
    else:
        data = {"bot": bot, "user": await db.fetchrow("SELECT name_cached AS username, avatar_cached AS avatar FROM servers WHERE guild_id = $1", target_id)}
    bot_obj = data["user"]
    
    if not bot_obj:
        return abort(404)

    if format == enums.WidgetFormat.json:
        return data

    if format == enums.WidgetFormat.html:
        rendered = await env.render_async(**{"textcolor": textcolor, "bgcolor": bgcolor, "id": target_id, "type": target_type.name} | data)
        return HTMLResponse(rendered)

    if format in (enums.WidgetFormat.png, enums.WidgetFormat.webp):
        # Check if in cache
        cache = await redis.get(cache_key)
        if cache and not no_cache:
            def _stream():
                with io.BytesIO(cache) as output:
                    yield from output

            return StreamingResponse(_stream(), media_type=f"image/{format.name}")

        widget_img = Image.new("RGBA", (300, 175), bgcolor)
        async with aiohttp.ClientSession() as sess:
            async with sess.get(data["user"]["avatar"]) as res:
                avatar_img = await res.read()

        static = request.app.state.static
        fates_pil = static["fates_pil"]
        votes_pil = static["votes_pil"]
        server_pil = static["server_pil"]
        avatar_pil = Image.open(io.BytesIO(avatar_img)).resize((100, 100))
        avatar_pil_bg = Image.new('RGBA', avatar_pil.size, (0,0,0))
        
        #pasting the bot image
        try:
            widget_img.paste(Image.alpha_composite(avatar_pil_bg, avatar_pil),(10,widget_img.size[-1]//5))
        except:
            widget_img.paste(avatar_pil,(10,widget_img.size[-1]//5))
        
        def remove_transparency(im, bgcolor):
            if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
                # Need to convert to RGBA if LA format due to a bug in PIL (http://stackoverflow.com/a/1963146)
                alpha = im.convert('RGBA').split()[-1]
    
                # Create a new background image of our matt color.
                # Must be RGBA because paste requires both images have the same format
                # (http://stackoverflow.com/a/8720632  and  http://stackoverflow.com/a/9459208)
                bg = Image.new("RGBA", im.size, bgcolor)
                bg.paste(im, mask=alpha)
                return bg
            return im
        widget_img.paste(remove_transparency(fates_pil, bgcolor),(10,152))
    
        #pasting servers logo
        widget_img.paste(
            server_pil,
            (120, 95) if desc_length != 0 else (120, 30)
        )

        #pasting votes logo
        widget_img.paste(
            votes_pil,
            (120, 115) if desc_length != 0 else (120, 50)
        )
    
        font = os.path.join("data/static/LexendDeca-Regular.ttf")

        def get_font(string: str, d):
            return ImageFont.truetype(
                font,
                get_font_size(d.textsize(string)[0]),
                layout_engine=ImageFont.LAYOUT_RAQM
            )
    
        def get_font_size(width: int):
            if width <= 90:
                return 18  
            if width >= 192:
                return 10
            if width == 168:
                return 12
            return 168-width-90
        
        def the_area(str_width: int, image_width: int):
            if str_width < 191:
                new_width=abs(int(str_width-image_width))
                return (new_width//2.5)
            new_width=abs(int(str_width-image_width))
            return (new_width//4.5)
         
            #lists name
        d = ImageDraw.Draw(widget_img)
        d.text(
            (25,150), 
            'Fates List', 
            fill=textcolor,
            font=ImageFont.truetype(
                font,
                10,
                layout_engine=ImageFont.LAYOUT_RAQM
            )
        )

        #Bot name
        d.text(
            (
                the_area(
                    d.textsize(str(bot_obj['username']))[0],
                    widget_img.size[0]
                ),
            5), 
            str(bot_obj['username']), 
            fill=textcolor,
            font=ImageFont.truetype(
                font,
                16,
                layout_engine=ImageFont.LAYOUT_RAQM)
            )
    
        bot["description"] = bot["description"].encode("ascii", "ignore").decode()

        # description
        if desc_length != 0: 
            wrapper = textwrap.TextWrapper(width=15)
            text = cd or (bot["description"][:desc_length] if desc_length > 0 else bot["description"])
            word_list = wrapper.wrap(text=str(text))
            d.text(
                (120,30), 
                str("\n".join(word_list)), 
                fill=textcolor,
                font=get_font(str("\n".join(word_list)),d)
            )
    
        #server count
        d.text(
            (140,94) if desc_length != 0 else (140,30), 
            human_format(bot["guild_count"]), 
            fill=textcolor,
            font=get_font(human_format(bot["guild_count"]),d)
        )
    
        #votes
        d.text(
            (140,114) if desc_length != 0 else (140,50),
            human_format(bot["votes"]), 
            fill=textcolor,
            font=get_font(human_format(bot['votes']),d)
        )
        
        output = io.BytesIO()
        widget_img.save(output, format=format.name.upper())
        output.seek(0)
        await redis.set(cache_key, output.read(), ex=60*3)
        output.seek(0)

        def _stream():    
            yield from output
            output.close()

        return StreamingResponse(_stream(), media_type=f"image/{format.name}")

