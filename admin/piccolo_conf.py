import sys

from piccolo.conf.apps import AppRegistry
from piccolo.engine.postgres import PostgresEngine

sys.path.append("..")
from config import pg_pwd, pg_user

DB = PostgresEngine(config={
    "database": "fateslist",
    "user": pg_user,
    "host": "localhost",
    "port": 12345,
})


# A list of paths to piccolo apps
# e.g. ['blog.piccolo_app']
APP_REGISTRY = AppRegistry(apps=["admin_v2.piccolo_app", "piccolo.apps.user.piccolo_app", "piccolo_admin.piccolo_app"])
