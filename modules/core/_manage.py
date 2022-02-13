# pylint: disable=E1101
"""_manage comtains functions to manage the site using dragon"""
import asyncio
import datetime
import importlib
import io
import multiprocessing
import os
import secrets
import shutil
import signal
import sys
import time
import uuid
import warnings
from getpass import getpass
from pathlib import Path
from subprocess import DEVNULL, Popen
from typing import Any, Callable, Dict

sys.pycache_prefix = "data/pycache"
if sys.version_info < (3, 11):
    warnings.warn(
        f"Fates List has only been tested to run on python 3.11. You are running {sys.version_info}",
        RuntimeWarning,
    )


def error(msg: str, code: int = 1):
    print(msg)
    return sys.exit(code)


def confirm(msg, abort: bool = True):
    while True:
        check = input(msg + "(Y/N): ")
        if check.lower() in ("y", "yes"):
            return True
        if check.lower() in ("n", "no"):
            if abort:
                sys.exit(1)
            return False


def _fappgen(session_id, workers, static_assets):
    """Make the FastAPI app for gunicorn"""
    from fastapi import FastAPI
    from fastapi.responses import ORJSONResponse

    from config import API_VERSION
    from modules.discord.api.v2.base import responses
    from modules.core.system import init_fates_worker

    _app = FastAPI(
        title="Fates List",
        responses=responses,
        description=f"""
            Current API: v2 beta 3
            Default API: v{API_VERSION}
            API URL: https://api.fateslist.xyz
            API Docs: https://apidocs.fateslist.xyz
            Enum Reference: https://apidocs.fateslist.xyz/structures/enums.autogen
        """,
        version="0.4.0",
        terms_of_service="https://fateslist.xyz/frostpaw/tos",
        license_info={
            "name": "MIT",
            "url": "https://github.com/Fates-List/FatesList/blob/main/LICENSE",
        },
        default_response_class=ORJSONResponse,
        redoc_url=f"/api/v{API_VERSION}/docs/redoc",
        docs_url=f"/api/v{API_VERSION}/docs/swagger",
        openapi_url=f"/api/v{API_VERSION}/docs/openapi",
        servers=[
            {
                "url": "https://api.fateslist.xyz",
                "description": "Fates List API"
            }, 
        ]
    )
    
    _app.state.static = static_assets

    @_app.on_event("startup")
    async def startup():
        await init_fates_worker(_app, session_id, workers)

    return _app


default_workers_num = (multiprocessing.cpu_count() * 2) + 1


def site_run():
    """Runs the Fates List site"""
    workers = os.environ.get("WORKERS") or default_workers_num
    workers = int(workers)

    from gunicorn.app.base import BaseApplication
    from PIL import Image

    from config._logger import logger

    session_id = uuid.uuid4()

    # Load in static assets for bot widgets
    static_assets = {}
    with open("data/static/botlisticon.webp", mode="rb") as res:
        static_assets["fates_img"] = io.BytesIO(res.read())

    with open("data/static/votes.png", mode="rb") as res:
        static_assets["votes_img"] = io.BytesIO(res.read())

    with open("data/static/server.png", mode="rb") as res:
        static_assets["server_img"] = io.BytesIO(res.read())

    static_assets["fates_pil"] = Image.open(static_assets["fates_img"]).resize(
        (10, 10))
    static_assets["votes_pil"] = Image.open(static_assets["votes_img"]).resize(
        (15, 15))
    static_assets["server_pil"] = Image.open(
        static_assets["server_img"]).resize((15, 15))

    # Create the pids folder if it hasnt been created
    Path("data/pids").mkdir(exist_ok=True)

    for sig in (signal.SIGINT, signal.SIGQUIT, signal.SIGTERM):
        signal.signal(sig, lambda *args, **kwargs: ...)

    class FatesRunner(BaseApplication):
        def __init__(self, application: Callable, options: dict[str, Any]):
            self.options = options
            self.application = application
            super().__init__()

        def load_config(self):
            config = {
                key: value
                for key, value in self.options.items()
                if key in self.cfg.settings and value is not None
            }
            for key, value in config.items():
                self.cfg.set(key.lower(), value)

        def load(self):
            return self.application

    options = {
        "worker_class": "config._uvicorn.FatesWorker",
        "workers": workers,
        "bind": "127.0.0.1:9999",
        "loglevel": "info",
        "pidfile": "data/pids/gunicorn.pid",
        "preload_app": True,
        "timeout": 120,
        "max_requests": 1000, # Currently there are bugs which prevent us from increasing this
    }

    _app = _fappgen(str(session_id), workers, static_assets)
    try:
        FatesRunner(_app, options).run()
    except BaseException as exc:
        logger.info(f"Site killed due to {type(exc).__name__}: {exc}")
        sys.exit(0)

def site_enum2html():
    """Converts the enums in modules/models/enums.py into markdown. Mainly for apidocs creation"""
    enums = importlib.import_module("modules.models.enums")
    aenum = importlib.import_module("aenum")
    md = {}
    md_path = Path("data/res/base_enum.md")
    with md_path.open() as f:
        base_md = f.read()

    for key in enums.__dict__.keys():
        # Ignore internal or dunder keys
        if key.startswith("_") or key in ("IntEnum", "Enum"):
            continue

        v = enums.__dict__[key]
        if isinstance(v, aenum.EnumType):
            props = list(v)
            try:
                fields = v._init_
            except AttributeError:
                fields = []
            md[key] = {}
            md[key]["doc"] = "\n"
            md[key]["table"] = "| Name | Value | Description |"
            nl = "\n| :--- | :--- | :--- |"
            keys = []
            for ext in fields:
                if ext in ("value", "__doc__"):
                    continue
                md[key][
                    "table"] += f" {ext.strip('_').replace('_', ' ').title()} |"
                nl += " :--- |"
                keys.append(ext)
            md[key]["table"] += f"{nl}\n"

            if v.__doc__ and v.__doc__ != "An enumeration.":
                md[key]["doc"] = "\n" + v.__doc__ + "\n\n"

            for prop in props:
                md[key][
                    "table"] += f"| {prop.name} | {prop.value} | {prop.__doc__} |"
                for prop_key in keys:
                    tmp = getattr(prop, prop_key)
                    try:
                        tmp = str(tmp) + f" ({tmp.value})"
                    except AttributeError:
                        tmp = str(tmp)
                    md[key]["table"] += f" {tmp} |"
                md[key]["table"] += "\n"

    md = dict(sorted(md.items()))

    md_out = []
    for key in md.keys():
        md_out.append(f'## {key}\n{md[key]["doc"]}{md[key]["table"]}')

    print(base_md + "\n" + "\n\n".join(md_out))

def site_getdragondocs():
    """Gets the dragon docs"""
    async def _docs():
        import builtins
        from fastapi import FastAPI # IPC needs it
        builtins.app = FastAPI()
        builtins.app.state.worker_session = FastAPI()
        builtins.app.state.worker_session.ipc_up = True
        import aioredis
        redis = aioredis.from_url("redis://localhost:1001", db=1)
        from modules.core.ipc import redis_ipc_new
        docs = await redis_ipc_new(redis, "DOCS")
        print(docs.decode())

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_docs())


def site_reload():
    """Get the PID of the running site and reloads the site"""
    try:
        with open("data/pids/gunicorn.pid") as guni_pid:
            pid = guni_pid.read().replace(" ", "").replace("\n", "")

            if not pid.isdigit():
                return error(
                    "Invalid/corrupt PID file found (site/gunicorn.pid)")

            pid = int(pid)
            if not os.environ.get("KILL"):
                os.kill(pid, signal.SIGHUP)
            else:
                try:
                    os.kill(pid, signal.SIGINT)
                except Exception as exc:
                    print(exc)
                print("Waiting for site to die...")
                time.sleep(3)
                # Use kill to force kill any rogue workers
                os.system('killall -9 "gunicorn: master" >/dev/null 2>&1')
                os.system('killall -9 "gunicorn: worker" >/dev/null 2>&1')
                time.sleep(3)

    except FileNotFoundError:
        return error("No PID file found. Is the site running?")


def site_venv():
    """Sets up a new venv deleting the old one"""
    from config._logger import logger

    python = os.environ.get("PYTHON") or "python3.11"
    home = os.environ.get("HOMEDIR") or Path.home()
    home = Path(str(home))

    logger.info("Backing up old venv")
    Path(home / "flvenv").rename(home / "flvenv.old")

    cmd = [python, "-m", "venv", str(home / "flvenv")]

    with Popen(cmd, env=os.environ) as proc:
        proc.wait()

    new_python = home / "flvenv/bin/python"

    cmd = [new_python, "-m", "pip", "install", "-r", "data/res/deps.txt"]

    with Popen(cmd, env=os.environ) as proc:
        proc.wait()


def site_updaterepos():
    """Update all of the extra internal services made by Fates List"""
    cmd = [
        "git",
        "submodule",
        "foreach",
        "--recursive",
        "git",
        "pull",
        "origin",
        "main",
    ]
    with Popen(cmd, env=os.environ) as proc:
        proc.wait()


def site_gensecret():
    """Generates a random secret"""
    print(secrets.token_urlsafe())


def site_compilestatic():
    """Compiles all labelled static files"""
    for src_file in Path("data/static/assets/src").rglob("*.js"):
        out_file = (str(src_file).replace(".js", ".min.js").replace(
            "src/", "prod/").replace("js/", ""))
        print(f"{src_file} -> {out_file}")
        cmd = [
            "google-closure-compiler",
            "--js",
            str(src_file),
            "--js_output_file",
            out_file,
        ]

        with Popen(cmd, env=os.environ) as proc:
            proc.wait()

    for src_file in Path("data/static/assets/src").rglob("*.scss"):
        out_file = (str(src_file).replace(".scss", ".min.css").replace(
            "src/", "prod/").replace("css/", ""))
        print(f"{src_file} -> {out_file}")
        cmd = ["sass", "--style=compressed", str(src_file), out_file]

        with Popen(cmd, env=os.environ) as proc:
            proc.wait()

    for img in Path("data/static/assets/src/img").rglob("*"):
        ext = str(img).split(".")[-1]
        out = str(img).replace("src/img/", "prod/").replace(f".{ext}", ".webp")
        print(f"{img} -> {out}")

        if ext == "webp":
            shutil.copy2(str(img), out)
        else:
            cmd = ["cwebp", "-quiet", "-q", "75", str(img), "-o", out]

            with Popen(cmd, env=os.environ) as proc:
                proc.wait()

def db_backup():
    """Backs up the Fates List database"""
    from config._logger import logger

    logger.info("Starting backups")

    bak_id = datetime.datetime.now().strftime("%Y-%m-%d~%H:%M:%S")
    cmd = f"pg_dump -Fc > /backups/full-{bak_id}.bak"

    with Popen(cmd, shell=True, env=os.environ) as proc:
        proc.wait()

    logger.info("Backup of full db done. Backing up only schema...")

    try:
        Path("/backups/latest.bak").unlink()
    except FileNotFoundError:
        pass

    Path("/backups/latest.bak").symlink_to(f"/backups/full-{bak_id}.bak")
    cmd = f"pg_dump -Fc --schema-only --no-owner > /backups/schema-{bak_id}.bak"

    with Popen(cmd, shell=True, env=os.environ) as proc:
        proc.wait()

    logger.info("Schema backup done")

    conf_pwd = getpass(prompt="Enter rclone conf password: ")
    for bak_type in ("full", "schema"):
        cmd = (
            f"rclone copy /backups/{bak_type}-{bak_id}.bak 'Fates List:fates_backups' "
        )
        cmd += f"--password-command 'printf {conf_pwd}'"

        with Popen(cmd, env=os.environ, shell=True) as proc:
            proc.wait()

    logger.success("Backups done!")


def db_shell():
    """Run a postgres shell"""
    with Popen(["pgcli"], env=os.environ) as proc:
        proc.wait()


def db_apply():
    """Apply Fates List database migration"""
    import uvloop

    from config._logger import logger

    uvloop.install()

    import aioredis
    import asyncpg

    module = os.environ.get("MIGRATION")

    if not module:
        raise RuntimeError(
            "No migration found. Set MIGRATION envvar to migration file path")

    try:
        migration = importlib.import_module(module)
        _ = migration.apply  # Check for apply function
    except Exception as exc:
        return error(f"Could not import migration file: {exc}")

    async def _migrator():
        postgres = await asyncpg.create_pool()
        redis = aioredis.from_url("redis://localhost:1001", db=1)
        logger.info("Starting migration")
        ret = await migration.apply(postgres=postgres,
                                    redis=redis,
                                    logger=logger)
        logger.success(f"Migration applied with return code of {ret}")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_migrator())


def db_wipeuser():
    """Wipes a user account (e.g. Data Deletion Request)"""
    import uvloop

    from config._logger import logger

    uvloop.install()

    import aioredis
    import asyncpg

    try:
        user_id = int(os.environ.get("USER"))
    except:
        user_id = None

    if not user_id:
        raise RuntimeError("Set USER envvar to user id to wipe")

    async def _wipeuser():
        logger.info("Wiping user info in db")
        db = await asyncpg.create_pool()
        await db.execute("DELETE FROM users WHERE user_id = $1", user_id)

        bots = await db.fetch(
            """SELECT DISTINCT bots.bot_id FROM bots 
            INNER JOIN bot_owner ON bot_owner.bot_id = bots.bot_id 
            WHERE bot_owner.owner = $1 AND bot_owner.main = true""",
            user_id,
        )
        for bot in bots:
            await db.execute("DELETE FROM bots WHERE bot_id = $1",
                             bot["bot_id"])

        votes = await db.fetch(
            "SELECT bot_id from bot_voters WHERE user_id = $1", user_id)
        for vote in votes:
            await db.execute(
                "UPDATE bots SET votes = votes - 1 WHERE bot_id = $1",
                vote["bot_id"])

        await db.execute("DELETE FROM bot_voters WHERE user_id = $1", user_id)

        logger.info("Clearing redis info on user...")
        redis = aioredis.from_url("redis://localhost:1001", db=1)
        await redis.hdel(str(user_id), "cache")
        await redis.hdel(str(user_id), "ws")

        await redis.close()
        logger.success("Done wiping user")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_wipeuser())


def db_setup():
    """Setup Snowfall (the Fates List database system)"""
    from config._logger import logger

    home = os.environ.get("HOMEDIR") or Path.home()
    home = Path(str(home))

    backup = os.environ.get("backup", False)
    if backup:
        backup = True

    confirm(
        "Setting up Snowfall databases is a potentially destructive operation. Continue?",
        abort=True,
    )
    logger.info("Preparing to setup snowtuft")

    if not home.exists():
        return error("Invalid user specified for primary_user")

    try:
        with open("/etc/sysctl.conf", "w") as sysctl_file:
            lines = ["fs.file-max=17500", "vm.overcommit_memory = 1"]
            sysctl_file.write("\n".join(lines))
    except:
        pass

    with Popen(["sysctl", "-p"], env=os.environ, stdout=DEVNULL) as proc:
        proc.wait()

    if Path("/snowfall/docker/env_done").exists():
        logger.info("Existing docker setup found. Backing it up...")
        try:
            if backup:
                db_backup()
        except Exception as exc:
            logger.error(f"Backup failed. Error is {exc}")
            confirm("Continue? ", abort=True)

        with Popen(["systemctl", "stop", "snowfall-dbs"],
                   env=os.environ) as proc:
            proc.wait()

    logger.info("Removing/Renaming old files")

    def _rm_force(f_name):
        try:
            Path(f_name).unlink()
        except Exception:
            pass

    _rm_force("/etc/systemd/system/snowfall-dbs.service")

    if Path("/snowfall").exists():
        uid = str(uuid.uuid4())
        logger.info(f"Moving /snowfall to /snowfall.old/{uid}")
        Path("/snowfall.old").mkdir(exist_ok=True)
        Path("/snowfall").rename(f"/snowfall.old/{uid}")

    Path("/snowfall/docker/db/postgres").mkdir(parents=True)
    Path("/snowfall/docker/db/redis").mkdir(parents=True)

    pg_pwd = secrets.token_urlsafe()

    with open("/snowfall/docker/env.pg", "w") as env_pg:
        lines = [
            "POSTGRES_DB=fateslist",
            "POSTGRES_USER=fateslist",
            f"POSTGRES_PASSWORD={pg_pwd}",
        ]
        env_pg.write("\n".join(lines))

    shutil.copytree("data/snowfall/docker/scripts",
                    "/snowfall/docker/scripts",
                    dirs_exist_ok=True)
    shutil.copy2("data/snowfall/docker/config/docker-compose.yml",
                 "/snowfall/docker")

    logger.info("Starting up docker compose...")
    cmd = [
        "docker-compose", "-f", "/snowfall/docker/docker-compose.yml", "up",
        "-d"
    ]

    with Popen(cmd, env=os.environ) as proc:
        proc.wait()

    time.sleep(5)

    logger.info("Fixing postgres password. Do not worry if this fails")

    cmd = [
        "docker",
        "exec",
        "snowfall.postgres",
        "psql",
        "-U",
        "fateslist",
        "-d",
        "fateslist",
        "-c",
        f"ALTER USER fateslist WITH PASSWORD '{pg_pwd}'",
    ]

    with Popen(cmd, env=os.environ) as proc:
        proc.wait()

    for op in ("start", "stop"):
        script_path = Path(f"/usr/bin/snowfall-dbs-{op}")
        with script_path.open("w") as action_script:
            lines = [
                "#!/bin/bash",
                f"/usr/bin/docker {op} snowfall.postgres",
                f"/usr/bin/docker {op} snowfall.redis",
            ]
            action_script.write("\n".join(lines))

        script_path.chmod(755)

    with open("/etc/systemd/system/snowfall-dbs.service", "w") as sf_service:
        lines = [
            "[Unit]",
            "Description=Docker Compose Snowfall 2.0",
            "Requires=docker.service",
            "After=docker.service",
            "",
            "[Service]",
            "Type=oneshot",
            "RemainAfterExit=yes",
            "WorkingDirectory=/snowfall/docker",
            "ExecStart=/usr/bin/snowfall-dbs-start",
            "ExecStop=/usr/bin/snowfall-dbs-stop"
            "TimeoutStartSec=0",
            "",
            "[Install]",
            "WantedBy=multi-user.target",
        ]

        sf_service.write("\n".join(lines))

    cmds = (
        ["systemctl", "daemon-reload"],
        ["snowfall-dbs-stop"],
        ["systemctl", "start", "snowfall-dbs"],
        ["systemctl", "restart", "snowfall-dbs"],
    )

    for cmd in cmds:
        with Popen(cmd, env=os.environ) as proc:
            proc.wait()

    time.sleep(2)

    logger.info("Fixing up user env")

    with open("/snowfall/userenv", "w") as sf_userenv:
        lines = [
            "source /etc/profile",
            "export PGUSER=fateslist",
            "export PGHOST=localhost",
            "export PGPORT=1000",
            f"export PGPASSWORD='{pg_pwd}'",
            "export PGDATABASE=fateslist",
        ]

        sf_userenv.write("\n".join(lines))

    lines = [
        "source /snowfall/userenv",
    ]

    with Path(home / ".bashrc").open("a") as bashrc_f:
        bashrc_f.write("\n".join(lines))

    with open("/root/.bashrc", "w") as bashrc_f:
        bashrc_f.write("\n".join(lines))

    if Path("/backups/latest.bak").exists():
        logger.info("Restoring backup...")

        with open("/tmp/s2.bash", "w") as sf_s2_f:
            lines = [
                "source /snowfall/userenv",
                'psql -c "CREATE ROLE meow"',
                'psql -c "CREATE ROLE readaccess"',
                'psql -c "CREATE ROLE postgres"',
                'psql -c "CREATE ROLE root"',
                'psql -c "CREATE SCHEMA IF NOT EXISTS public"',
                "psql -c 'CREATE EXTENSION IF NOT EXISTS " + '"uuid-ossp"' +
                "'",
                "pg_restore -cvd fateslist /backups/latest.bak",
            ]
            sf_s2_f.write("\n".join(lines))

        with Popen(["bash", "/tmp/s2.bash"]) as proc:
            proc.wait()

    Path("/snowfall/docker/env_done").touch()
    logger.info(f"Postgres password is {pg_pwd}")
    logger.success("Done setting up databases")
