from piccolo.conf.apps import AppRegistry
from piccolo.engine.postgres import PostgresEngine

DB = PostgresEngine(config={
    "database": "fateslist",
})


# A list of paths to piccolo apps
# e.g. ['blog.piccolo_app']
APP_REGISTRY = AppRegistry(apps=["piccolo_app", "piccolo.apps.user.piccolo_app", "piccolo_admin.piccolo_app"])
