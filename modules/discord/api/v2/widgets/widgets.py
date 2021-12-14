from modules.core import *
from lynxfall.utils.string import human_format
from fastapi.responses import PlainTextResponse, StreamingResponse
from PIL import Image, ImageDraw, ImageFont
import io, textwrap, aiofiles
from starlette.concurrency import run_in_threadpool
from math import floor

from ..base import API_VERSION

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/widgets",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Widgets"],
)


from colour import Color

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
async def get_widget(request: Request, bt: BackgroundTasks, target_id: int, target_type: enums.ReviewType, format: enums.WidgetFormat, bgcolor: Union[int, str] ='black', textcolor: Union[int, str] ='white', no_cache: Optional[bool] = False, cd: Optional[str] = None, full_desc: Optional[bool] = False):
    """
    Returns a widget

    cd - A custom description you wish to set for the widget

    full_desc - If this is set to true, the full description will be used, otherwise, only the first 25 characters will be used

    no_cache - If this is set to true, cache will not be used but will still be updated. If using cd, set this option to true and cache the image yourself
    Note that no_cache is slow and may lead to ratelimits and/or your got being banned if used excessively
    """
    if not is_color_like(str(bgcolor)) or not is_color_like(str(textcolor)):
        return abort(404)
    if isinstance(bgcolor, str):
        bgcolor=bgcolor.split('.')[0]
        bgcolor = floor(int(bgcolor)) if bgcolor.isdigit() or bgcolor.isdecimal() else bgcolor
    if isinstance(textcolor, str):
        textcolor=textcolor.split('.')[0]
        textcolor = floor(int(textcolor)) if textcolor.isdigit() or textcolor.isdecimal() else textcolor
        
    worker_session = request.app.state.worker_session
    db = worker_session.postgres
   
    if target_type == enums.ReviewType.bot:
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
    
    bt.add_task(add_ws_event, target_id, {"m": {"e": event}, "ctx": {"user": request.session.get('user_id'), "widget": True}}, type=_type)
    if target_type == enums.ReviewType.bot:
        data = {"bot": bot, "user": await get_bot(target_id, worker_session = request.app.state.worker_session)}
    else:
        data = {"bot": bot, "user": await db.fetchrow("SELECT name_cached AS username, avatar_cached AS avatar FROM servers WHERE guild_id = $1", target_id)}
    bot_obj = data["user"]
    
    if not bot_obj:
        return abort(404)

    if format == enums.WidgetFormat.json:
        return data

    if format == enums.WidgetFormat.html:
        return await templates.TemplateResponse("widget.html", {"request": request} | data)

    if format in (enums.WidgetFormat.png, enums.WidgetFormat.webp):
        # Check if in cache
        cache = await redis_db.get(f"widget-{target_id}-{target_type}-{format.name}-{textcolor}")
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
    
        #pasting votes logo
        try:
            widget_img.paste(Image.alpha_composite(avatar_pil_bg, votes_pil),(120,115))
        except:
            widget_img.paste(votes_pil,(120,115))
    
        #pasting servers logo
        try:
            widget_img.paste(Image.alpha_composite(avatar_pil_bg, server_pil),(120,95))
        except:
            widget_img.paste(server_pil,(120,95))

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
                5
            ), 
            str(bot_obj['username']), 
            fill=textcolor,
            font=ImageFont.truetype(
                font,
                16,
                layout_engine=ImageFont.LAYOUT_RAQM
                )
            )
    
        #description
        wrapper = textwrap.TextWrapper(width=15)
        text = cd or (bot["description"][:25] if not full_desc else bot["description"])
        word_list = wrapper.wrap(text=str(text))
        d.text(
            (120,30), 
            str("\n".join(word_list)), 
            fill=textcolor,
            font=get_font(str("\n".join(word_list)),d)
        )
    
        #server count
        d.text(
            (140,94), 
            human_format(bot["guild_count"]), 
            fill=textcolor,
            font=get_font(human_format(bot["guild_count"]),d)
        )
    
        #votes
        d.text(
            (140,114),
            human_format(bot["votes"]), 
            fill=textcolor,
            font=get_font(human_format(bot['votes']),d)
        )
        
        output = io.BytesIO()
        widget_img.save(output, format=format.name.upper())
        output.seek(0)
        await redis_db.set(f"widget-{target_id}-{target_type}-{format.name}-{textcolor}", output.read(), ex=60*3)
        output.seek(0)

        def _stream():    
            yield from output
            output.close()

        return StreamingResponse(_stream(), media_type=f"image/{format.name}")

