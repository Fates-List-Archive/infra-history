import sys
sys.path.append(".")
sys.path.append("../../../")
from fastapi import FastAPI, Request
from fastapi.responses import ORJSONResponse
from piccolo.engine import engine_finder
from piccolo_admin.endpoints import create_admin
from piccolo_api.crud.endpoints import PiccoloCRUD
from piccolo_api.fastapi.endpoints import FastAPIWrapper
from starlette.routing import Mount
from tables import Bot, Review, BotTag, User, Vanity

admin = create_admin([Vanity, User, Bot, BotTag, Review], allowed_hosts = ["lynx.fateslist.xyz"], production = True)
app = FastAPI(routes=[Mount("/", admin)])

@app.on_event("startup")
async def startup():
    engine = engine_finder()
    await engine.start_connection_pool()

@app.on_event("shutdown")
async def close():
    await engine.close_connection_pool()
