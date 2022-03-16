Well, all of you have probably noticed by now (*assuming you actually read URLs. Crazy, I know...*) but there has been quite a few changes regarding our tech stack lately.

### The Old Stack

Our old stack was rather... *well*... hard to maintain, had poor project structure and tended to have tons of broken SQL and 500 errors randomly. It was a [FastAPI](https://fastapi.tiangolo.com) app with over a few thousand lines of Python (no offense to FastAPI or Python, this was really my first serious webdev project and at the time I didn't really know much about FastAPI or web development in general).

One of the other issues was regards to our frontend, FastAPI's jinja2 templating, while easy, required us to create custom functions to handle the common logic (Discord User ID etc.) for templating which quickly turned into a large unreadable mess. FastAPI was still at it's infancy stage and so large amounts of custom code was required some of which was (and this was unrelated to [Fates List](https://fateslist.xyz)) eventually added to FastAPI later on. 

None of this was helped by the fact that Fates List was originally coded using Termius on an iPad Air 2 (later a iPad Air 4) using Termius. Writing Python code using a on-screen keyboard isn't really as productive as doing it now on a Apple M1 Macbook Air...

As an example of templating bloat, here's what our templating system looked like:

```py
class templates():
    @staticmethod
    async def TemplateResponse(f, arg_dict: dict, *, context: dict = {}, not_error: bool = True, compact: bool = True):
        request = arg_dict["request"]
        worker_session = request.app.state.worker_session
        db = worker_session.postgres
        status = arg_dict.get("status_code")
        if "user_id" in request.session.keys():
            user_data = await db.fetchrow("SELECT state, user_css, api_token, site_lang FROM users WHERE user_id = $1", int(request.session["user_id"]))
            state, arg_dict["user_css"], arg_dict["user_token"], arg_dict["site_lang"] = user_data["state"], user_data["user_css"], user_data["api_token"], user_data["site_lang"]
            if (state == enums.UserState.global_ban) and not_error:
                ban_type = enums.UserState(state).__doc__
                return await templates.e(request, f"You have been {ban_type} banned from Fates List", status_code = 403)
            if not compact:
                arg_dict["staff"] = (await is_staff(None, int(request.session["user_id"]), 2))[2]
            arg_dict["avatar"] = request.session.get("avatar")
            arg_dict["username"] = request.session.get("username")
            arg_dict["user_id"] = int(request.session.get("user_id"))
        else:
            arg_dict["staff"] = [False]
            arg_dict["site_lang"] = "en"
        arg_dict["site_url"] = site_url
        arg_dict["data"] = arg_dict.get("data")
        arg_dict["path"] = request.url.path
        arg_dict["enums"] = enums
        arg_dict["len"] = len
        arg_dict["ireplace"] = ireplace
        arg_dict["ireplacem"] = ireplacem
        arg_dict["intl_text"] = intl_text # This comes from lynxfall.utils.string
        base_context = {
            "user_id": str(arg_dict["user_id"]) if "user_id" in arg_dict.keys() else None,
            "user_token": arg_dict.get("user_token"),
            "site_lang": arg_dict.get("site_lang"),
            "logged_in": "user_id" in arg_dict.keys(),
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
```

What FastAPI *shines* at is in backend. It has OpenAPI documentation and tons of useful additions for *creating APIs*. For example, you can directly return ``asyncpg.Record`` objects without custom serialization! FastAPI also has the handy ``jsonable_encoder`` function which turns python objects into JSON-serializable ones which was sadly never utilized as I never knew about them until starting with Lynx. This meant that creating APIs was much simpler on FastAPI than on other Python web frameworks. Developing full-blown sites on it that are meant to be used by a large number of people was not so easy.

### JS, the last straw

Well, if it ain't broke, don't fix it! We used to serve JS by using JsDelivr and tons of ?v= query params whenever we changed the JS. This quickly became a bad idea. Large amounts of code was made to automatically change JS file names and then later the move to query parameters made all the old work redundant.

Lots of changes were happening at the same time. RabbitMQ, due to high memory usage and just being overkill was removed and replaced with a golang service called ``dragon`` and later ``flamepaw``.

### Sunbeam

The first thing we did was rewriting the frontend. We chose to keep the FastAPI backend for now (though this ultimately did change). The FastAPO backend would return JSON which our frontend would then consume and render. [Sveltekit](https://kit.svelte.dev/) was chosen due to Svelte's simplicity. This turned out to be rather easy although Sveltekit, like FastAPI was new and documentation was lacking. A bit of struggle and the frontend was ultimately rewritten. The name chosen was **Sunbeam**. 

Cloudflare Pages was chosen and we got added to the 'Fast Builds Beta' program (which is actually faster). Sunbeam performs much more performantly thanks to these changes which has allowed for a greater userbase

At the launch of the rewrite, things broke due to a cache issue. Even now, I still don't know the cause. It fixed itself magically after I changed a few lines of code and prayed to God, but it ultimately started working well. 

One other struggle with the rewrite was global CSS styles. I eventually did a bit of reading and got it fixed using ``:global()``.

But other than that, Sunbeam was globally rolled out without a hitch, no issues really whatsoever!

### Gunicorn Pain

Another pain was actually programatically calling gunicorn. I wanted to do extra startup tasks and maintaining shell scripts was rather messy and tended to randomly fail. So this 'solution' was made:

```py
default_workers_num = lambda: (multiprocessing.cpu_count() * 2) + 1

def _fappgen(session_id, workers):
    """Make the FastAPI app for gunicorn"""
    from fastapi import FastAPI
    from fastapi.responses import ORJSONResponse
    from modules.core.system import init_fates_worker
     
    _app = FastAPI(
        title="Fates List",
        description="""
            Current API: v2 beta 3
            Default API: v2
            API Docs: https://apidocs.fateslist.xyz
        """,
        version="0.2.0",
        default_response_class=ORJSONResponse, 
        redoc_url=f"/api/v{API_VERSION}/docs/redoc",
        docs_url=f"/api/v{API_VERSION}/docs/swagger",
        openapi_url=f"/api/v{API_VERSION}/docs/openapi"
    )

    @_app.on_event("startup")
    async def startup():
        await init_fates_worker(_app, session_id, workers)
    
    return _app

@site.command("run")
def run_site(
    workers: int = typer.Argument(default_workers_num, envvar="SITE_WORKERS"),
):
    """Runs the Fates List site"""
    from gunicorn.app.base import BaseApplication

    session_id = uuid.uuid4()
    
    # Create the pids folder if it hasnt been created
    Path("data/pids").mkdir(exist_ok = True)
   
    for sig in (signal.SIGINT, signal.SIGQUIT, signal.SIGTERM):
        signal.signal(sig, lambda *args, **kwargs: ...)
    
    class FatesRunner(BaseApplication):
        def __init__(self, application: Callable, options: Dict[str, Any] = {}):
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
        "bind": "0.0.0.0:9999",
        "loglevel": "debug",
        "pidfile": "data/pids/gunicorn.pid"
    }
    
    app = _fappgen(str(session_id), workers)
    try:
        FatesRunner(app, options).run()
    except BaseException as exc:
        logger.info(f"{type(exc).__name__}: {exc}")
```

As you can see, quite a bit of boilerplate and this isn't even ``modules/core/system.py``!

Oh and by the way, here's a old version of ``manage.py`` happening a few months before the final backend rewrite: [https://github.com/Fates-List/infra/blob/514039d071ed1fc4f7108db4a6abcb57fc378b95/manage.py](https://github.com/Fates-List/infra/blob/514039d071ed1fc4f7108db4a6abcb57fc378b95/manage.py)

### Bloated Middleware Memes

And lastly, there was a large complex beast called "middleware" that frequently died and crashed breaking the site:

```py
class FatesListRequestHandler(BaseHTTPMiddleware):
    """Request Handler for Fates List"""
    def __init__(self, app, *, exc_handler):
        super().__init__(app)
        self.exc_handler = exc_handler
        
        # Methods that should be allowed by CORS
        self.cors_allowed = "GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS"
    
        # Default response
        self.default_res = HTMLResponse(
            "Something happened!", 
            status_code=500
        ) 
    
    @staticmethod
    def _log_req(path, request, response):
        """Logs HTTP requests to console (and file)"""
        code = response.status_code
        phrase = HTTPStatus(response.status_code).phrase
        query_str_raw = request.scope["query_string"]

        if query_str_raw:
            query_str = f'?{query_str_raw.decode("utf-8")}'
        else:
            query_str = ""
            
        logger.info(
            f"{request.method} {path}{query_str} | {code} {phrase}"
        )
        
    async def dispatch(self, request, call_next):
        """Run _dispatch, if that fails, log error and do exc handler"""
        request.state.error_id = str(uuid.uuid4())
        request.state.curr_time = str(datetime.datetime.now())
        path = request.scope["path"]

        try:
            res = await self._dispatcher(path, request, call_next)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Site Error Occurred") 
            res = await self.exc_handler(request, exc, log=True)
        
        self._log_req(path, request, res)
        return res if res else self.default_res
    
    async def _dispatcher(self, path, request, call_next):
        """Actual middleware"""
        if request.app.state.worker_session.dying:
            return HTMLResponse("Fates List is going down for a reboot")
        
        logger.trace(request.headers.get("X-Forwarded-For"))
        
        if path.startswith("/bots/"):
            path = path.replace("/bots", "/bot", 1)
        
        # These are checks path should not start with
        is_api = path.startswith("/api")
        request.scope["path"] = path
        
        if is_api:
            # Handle /api as /api/vX excluding docs + pinned requests
            request.scope, api_ver = api_versioner(request, API_VERSION)
    
        start_time = time.time()
        
        # Process request with retry
        try:
            response = await call_next(request)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Site Error Occurred")
            response = await self.exc_handler(request, exc)

        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        if is_api:
            response.headers["X-API-Version"] = api_ver
    
        # Fuck CORS by force setting headers with proper origin
        origin = request.headers.get('Origin')

        # Make commonly repepated headers shorter
        acac = "Access-Control-Allow-Credentials"
        acao = "Access-Control-Allow-Origin"
        acam = "Access-Control-Allow-Methods"

        response.headers[acao] = origin if origin else "*"
        
        if is_api and origin:
            response.headers[acac] = "true"
        else:
            response.headers[acac] = "false"
        
        response.headers[acam] = self.cors_allowed
        if response.status_code == 405:
            if request.method == "OPTIONS" and is_api:
                response.status_code = 204
                response.headers["Allow"] = self.cors_allowed
       
        return response
```

Yes, I know, ``CORSMiddleware`` exists. When I first made this bloat-code, I didn't see it or think to implement it. But API versioning in FastAPI (or even ``actix-web``) is not included "out of the box" which made things slightly harder.


### Discord pains, the last straw for backend

Due to how gunicorn (this was the recommended way to deploy FastAPI+uvicorn sites at the time) handles workers, we also had to start multiple discord.py instances, sometimes up to 10-12 depending on how many workers we needed/wanted. The site had numerous performance and architectural issues. This lead to ratelimit issues.

The bloat code and the added ``WorkerSession`` code was even more bloat on top. Figuring out how to start a ``discord.py`` session in FastAPI took a bit of work and banging my head.

```py
class FatesWorkerSession(Singleton):  # pylint: disable=too-many-instance-attributes
    """Stores a worker session"""

    def __init__(
        self,
        *, 
        session_id: str,
        postgres: asyncpg.Pool,
        redis: aioredis.Connection,
        rabbit: aio_pika.RobustConnection,
        worker_discord: FatesWorkerDiscord, 
        oauth: FatesWorkerOauth
    ):
        self.id = session_id
        self.postgres = postgres
        self.redis = redis
        self.rabbit = rabbit
        self.discord = worker_discord
        self.oauth = oauth
        
        # Record basic stats and initially set workers to None
        self.start_time = time.time()
        self.up = False
        self.workers = None
        
        # FUP = finally up/all workers are now up
        self.fup = False
        
        # Used in shutdown to check if already dead
        self.dying = False
        
        # Templating
        self.templates = Jinja2Templates(directory="data/templates")

    def set_up(self):
        """Set the worker to up"""
        self.up = True

    def publish_workers(self, workers):
        """Publish workers"""
        self.workers = workers
        self.workers.sort()
        self.fup = True

    def primary_worker(self):
        """Returns if we are primary (first) worker"""
        return self.fup and self.workers[0] == os.getpid()

    def get_worker_index(self):
        """
        This function should only be called 
        after workers are published
        """
        return self.workers.index(os.getpid())


def setup_discord():
    """Sets up discord clients"""
    intent_main = discord.Intents(
        guilds=True,
        members=True,
        presences=True
    )
    intent_servers = discord.Intents(
        guilds = True
    )
    intent_dbg = discord.Intents(
        dm_messages = True  # Only allow DMs to pass through
    ) 
    client = FatesBot(intents=intent_main)
    client_server = FatesBot(intents=intent_servers)
    client_dbg = FatesDebugBot(intents=intent_dbg)
    logger.info("Discord init is beginning")
    asyncio.create_task(client.start(TOKEN_MAIN))
    asyncio.create_task(client_server.start(TOKEN_SERVER))
    return {"main": client, "servers": client_server, "debug": client_dbg}
```

Ultimately, the code was clunky, crashed very frequently and once even got to the ``IDENTITY`` limit and had our token reset

It was very clear our code was not going to work well.

### IPC, a solution?

Lynxfall RabbitMQ was extended using Redis IPC to solve this issue. Instead of multiple sessions to discord, we had a python IPC system (hooked onto the old RabbitMQ worker code) that handled all interactions with the Discord API.

We did this using redis PUBSUB using the ``aioredis`` library.

This too, was ultimately a failure. The python code randomly either failed to listen to redis or had random ``asyncio.CancelledError``'s that I really didn't want to deal with.

RabbitMQ was also getting harder and harder to justify and took up a large part of our memory usage. It was ultimately moved to the API itself as RabbitMQ didn't give us too much for what it was doing.

**Lesson:** Don't use a Message Queue when you don't need one and don't extend it with a bloated IPC using hacks on your startup scripts.

### Entering Golang

Golang was the ultimate second rewrite of IPC and it was at the time much better. We still used Redis IPC but our golang code was much faster and ultimately replaced Lynxfall RabbitMQ workers.

Golang ultimately ate up the rest of our non-essential python services during discord.py's initial deprecation. 

But the IPC protocol itself was bloated with a new ``wait_for_ipc`` system in FastAPI that was also beginning to fail now. A refactored ``flamepaw`` made it slightly more reliable but still unreliable:

```py
    # This is still builtins for backward compatibility. 
    # ========================================================
    # Move all code to use worker session. All new code should 
    # always use worker session instead of builtins
    dbs = await setup_db()

    # Wait for redis ipc to come up
    app.state.first_run = True

    async def wait_for_ipc(first_run: bool = False):
        logger.info("Wait for ipc called")
        ipc_up = False
        if not first_run:
            app.state.worker_session.up = False

        while not ipc_up:
            resp = await redis_ipc_new(dbs["redis"], "PING", timeout=5)
            logger.info(resp)
            if not resp:
                invalid = True
                reason = "IPC not up"
            else:
                resp1 = resp.decode("utf-8")
                invalid, reason = False, "All good!"
                respl = resp1.split(" ")
                if len(respl) != 3:
                    invalid, reason = True, "Invalid PONG payload"
                if respl[0] != "PONG":
                    invalid, reason = True, "IPC corrupt"
                if respl[1] != "V3":
                    invalid, reason = True, f"Invalid IPC version: {respl[1]}"

                if not invalid:
                    app.state.site_degraded = (respl[2] == "1")
        
            if invalid:  # pylint: disable=no-else-continue
                logger.info(f"Invalid IPC. Got invalid PONG: {resp} (reason: {reason})")
                continue

            if first_run:
                return await finish_init(app, session_id, workers, dbs)
            app.state.worker_session.up = True
            return

    app.state.wait_for_ipc = wait_for_ipc
```

Oh and also, this code relies on a back on top of ``builtins`` meaning Pylance syntax highlighting (at this point, I was using a M1 Mac and not a iPad for coding) just didn't work.

Also, IPC was still bloated, here was the golang code:

```go
const (
	workerChannel     string        = "_worker_fates"
	commandExpiryTime time.Duration = 30 * time.Second
	ipcVersion        string        = "3"
)

var (
	ctx                  = context.Background()
	connected   bool     = false
	ipcIsUp     bool     = true
	pids        []string // Just use string slice here for storage of pids
	sessionId   string   // Session id
	degraded    int      = 0
	degradedStr string   = strconv.Itoa(degraded)
	guilds      []string
	allowCmd    bool = true
	pubsub      *redis.PubSub
)

var ipcActions = make(map[string]types.IPCCommand)

func ElementInSlice[T comparable](slice []T, elem T) bool {
	for i := range slice {
		if slice[i] == elem {
			return true
		}
	}
	return false
}

func setupCommands() {
	// Define all IPC commands here

	// PING <COMMAND ID>
	ipcActions["PING"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			return "PONG V" + ipcVersion + " " + degradedStr
		},
		MinArgs: -1,
		MaxArgs: -1,
	}

	// ROLES <COMMAND ID> <USER ID>
	// Returns roles as space seperated string on success
	ipcActions["ROLES"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			// Try to get from cache
			res := context.Redis.Get(ctx, "roles-"+cmd[2]).Val()
			if res == "" {
				member, err := common.DiscordMain.State.Member(common.MainServer, cmd[2])
				if err != nil {
					log.Warn(err)
					res = "-1"
				} else {
					res = strings.Join(member.Roles, " ")
					context.Redis.Set(ctx, "roles-"+cmd[2], res, 120*time.Second)
				}
			}
			return res
		},
		MinArgs: 3,
		MaxArgs: 3,
	}

	// GETPERM <COMMAND ID> <USER ID>
	ipcActions["GETPERM"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			perms, _, _ := common.GetPerms(common.DiscordMain, cmd[2], 0)
			res, err := json.Marshal(perms)
			if err != nil {
				log.Warn(err)
				return "-1"
			}
			return string(res)
		},
		MinArgs: 3,
		MaxArgs: 3,
	}

	// CMDLIST <COMMAND ID>
	ipcActions["CMDLIST"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			return spew.Sdump("IPC Commands loaded: ", ipcActions)
		},
	}

	// DOCS
	ipcActions["DOCS"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			return webserver.Docs
		},
	}
}

func StartIPC(postgres *pgxpool.Pool, redisClient *redis.Client) {
	setupCommands()
	u_guilds, err := common.DiscordMain.UserGuilds(100, "", "")
	if err != nil {
		panic(err)
	}

	for _, u_guild := range u_guilds {
		log.Info("Got guild ", u_guild.ID, " for precense check")
		guilds = append(guilds, u_guild.ID)
	}

	pubsub = redisClient.Subscribe(ctx, workerChannel)
	defer pubsub.Close()
	_, err = pubsub.Receive(ctx)
	if err != nil {
		panic(err)
	}

	ch := pubsub.Channel()

	ipcContext := types.IPCContext{
		Redis:    redisClient,
		Postgres: postgres,
	}

	handleMsg := func(msg redis.Message) {
		op := strings.Split(msg.Payload, " ")
		if len(op) < 2 {
			return
		}

		log.WithFields(log.Fields{
			"name": op[0],
			"args": op[1:],
			"pids": pids,
		}).Info("Got IPC Command ", op[0])

		cmd_id := op[1]

		if val, ok := ipcActions[op[0]]; ok {
			// Check minimum args
			if len(op) < val.MinArgs && val.MinArgs > 0 {
				return
			}

			// Similarly, check maximum
			if len(op) > val.MaxArgs && val.MaxArgs > 0 {
				return
			}

			res := val.Handler(op, ipcContext)
			redisClient.Set(ctx, cmd_id, res, commandExpiryTime)
		}
	}

	for msg := range ch {
		if allowCmd {
			go handleMsg(*msg)
		}
	}
}

func SignalHandle(s os.Signal, rdb *redis.Client) {
	allowCmd = false
	if ipcIsUp {
		ipcIsUp = false
		send_err := rdb.Publish(ctx, workerChannel, "RESTART *").Err()
		if send_err != nil {
			log.Error(send_err)
		}
		pubsub.Close()
		time.Sleep(1 * time.Second)
	}
}
```

``flamepaw`` now handles so much that a pinger was made to temporarily work around issues (such as a golang panic) and the pinger was a hack on top of ``tmux send-keys``, our process manager.

### Solution: Lightleap and Baypaw

The final solution: ``Lightleap`` and ``Baypaw``!

**Lightleap:** I started toying with Rust and ultimately rewrote all of the old FastAPI code in it. Lightleap uses the ``actix-web`` framework and it's less boilerplaty!

As an example:

```rust
HttpServer::new(move || {
    let cors = Cors::default()
        .allowed_origin_fn(|origin, _req_head| {
            origin.as_bytes().ends_with(b"fateslist.xyz")
        })
        .allowed_methods(vec!["GET", "HEAD", "PUT", "POST", "PATCH", "DELETE", "OPTIONS"])
        .allowed_headers(vec![
            http::header::AUTHORIZATION, 
            http::header::ACCEPT, 
            http::header::CONTENT_TYPE, 
            http::header::HeaderName::from_bytes(b"Frostpaw").unwrap(),
            http::header::HeaderName::from_bytes(b"Frostpaw-Auth").unwrap(),
            http::header::HeaderName::from_bytes(b"Frostpaw-Server").unwrap(),
            http::header::HeaderName::from_bytes(b"Frostpaw-Token").unwrap(),
            http::header::HeaderName::from_bytes(b"Frostpaw-Vote-Page").unwrap(),
            http::header::HeaderName::from_bytes(b"Frostpaw-Invite").unwrap(),
            http::header::HeaderName::from_bytes(b"Method").unwrap()
        ])
        .supports_credentials()
        .max_age(3600);
    App::new()
        .app_data(app_state.clone())
        .app_data(
            web::JsonConfig::default()
                .limit(1024 * 1024 * 10)
                .error_handler(|err, _req| actix_handle_err(err)),
        )
        .app_data(web::QueryConfig::default().error_handler(|err, _req| actix_handle_err(err)))
        .app_data(web::PathConfig::default().error_handler(|err, _req| actix_handle_err(err)))
        .wrap(cors)
        .wrap(middleware::Compress::default())
        .wrap(Logger::default())
        .wrap(middleware::NormalizePath::new(middleware::TrailingSlash::MergeOnly))
        .wrap_fn(|mut req, srv| {
            // Adapted from https://actix.rs/actix-web/src/actix_web/middleware/normalize.rs.html#89
            let head = req.head_mut();

            let original_path = head.uri.path();
            let path = original_path.replacen("/api/v2/", "/", 1);

            let mut parts = head.uri.clone().into_parts();
            let query = parts.path_and_query.as_ref().and_then(actix_web::http::uri::PathAndQuery::query);

            let path = match query {
                Some(q) => Bytes::from(format!("{}?{}", path, q)),
                None => Bytes::copy_from_slice(path.as_bytes()),
            };
            parts.path_and_query = Some(PathAndQuery::from_maybe_shared(path).unwrap());

            let uri = Uri::from_parts(parts).unwrap();
            req.match_info_mut().get_mut().update(&uri);
            req.head_mut().uri = uri;

            srv.call(req).map(|res| {
                res
            })
        })    
        .default_service(web::route().to(not_found))
```

Much simpler code and it handles both our API versioning, CORS and startup with workers!

A route in ``Lightleap``: 


```rust
#[get("/index")]
async fn index(req: HttpRequest, info: web::Query<models::IndexQuery>) -> Json<models::Index> {
    let mut index = models::Index::new();

    let data: &models::AppState = req.app_data::<web::Data<models::AppState>>().unwrap();

    if info.target_type.as_ref().unwrap_or(&"bot".to_string()) == "bot" {
        let cache = data.database.get_index_bots_from_cache().await;
        
        if cache.is_some() {
            return Json(cache.unwrap());
        }

        index.top_voted = data.database.index_bots(models::State::Approved).await;
        index.certified = data.database.index_bots(models::State::Certified).await;
        index.tags = data.database.bot_list_tags().await;
        index.new = data.database.index_new_bots().await;
        index.features = data.database.bot_features().await;

        data.database.set_index_bots_to_cache(&index).await;
    } else {
        let cache = data.database.get_index_servers_from_cache().await;
        
        if cache.is_some() {
            return Json(cache.unwrap());
        }

        index.top_voted = data.database.index_servers(models::State::Approved).await;
        index.certified = data.database.index_servers(models::State::Certified).await;
        index.new = data.database.index_new_servers().await;
        index.tags = data.database.server_list_tags().await;

        data.database.set_index_servers_to_cache(&index).await;
    }
    Json(index)
}
```

Much cleaner than the python equivalent:

```py
async def render_index(request: Request, api: bool, type: enums.ReviewType = enums.ReviewType.bot):
    worker_session = request.app.state.worker_session
    top_voted = await do_index_query(worker_session, add_query = "ORDER BY votes DESC", state = [0], type=type)
    new_bots = await do_index_query(worker_session, add_query = "ORDER BY created_at DESC", state = [0], type=type)
    certified_bots = await do_index_query(worker_session, add_query = "ORDER BY votes DESC", state = [6], type=type)

    if type == enums.ReviewType.bot:
        tags = tags_fixed
    else:
        tags = await db.fetch("SELECT id, name, iconify_data, owner_guild FROM server_tags")

    base_json = {
        "tags_fixed": tags, 
        "top_voted": top_voted, 
        "new_bots": new_bots, 
        "certified_bots": certified_bots, 
    }

    if type == enums.ReviewType.server:
        context = {"type": "server", "index": "/servers"}
    else:
        context = {"type": "bot"}

    if not api:
        return await templates.TemplateResponse("index.html", {"request": request, "random": random} | context | base_json, context = context)
    return base_json

@router.get("/")
@router.head("/")
async def index_fend(request: Request):
    return await render_index(request = request, api = False)
```

This doesn't include the actual db call either:

**Python DB code**

```py
async def parse_index_query(
    worker_session,
    fetch: List[asyncpg.Record],
    type: enums.ReviewType = enums.ReviewType.bot,
    **kwargs
) -> list:
    """
    Parses a index query to a list of partial bots
    """
    lst = []
    for bot in fetch:
        banner_replace_tup = (
            ('"', ""),
            ("'", ""),
            ("http://", "https://"),
            ("file://", ""),
        )
        if bot.get("flags") and flags_check(bot["flags"], enums.BotFlag.system):
            continue
        if type == enums.ReviewType.server:
            bot_obj = dict(bot) | {
                "user":
                await db.fetchrow(
                    "SELECT guild_id AS id, name_cached AS username, avatar_cached AS avatar FROM servers WHERE guild_id = $1",
                    bot["guild_id"],
                ),
                "bot_id":
                str(bot["guild_id"]),
                "banner":
                ireplacem(banner_replace_tup, bot["banner"])
                if bot["banner"] else None,
            }
            bot_obj |= bot_obj["user"]
            if not bot_obj["description"]:
                bot_obj["description"] = await default_server_desc(
                    bot_obj["user"]["username"], bot["guild_id"])
            lst.append(bot_obj)
        else:
            _user = await get_bot(bot["bot_id"], worker_session=worker_session)
            if _user:
                if _user.get("username", "").startswith("Deleted User "):
                    continue
                bot_obj = (dict(bot)
                           | {
                               "user":
                               _user,
                               "bot_id":
                               str(bot["bot_id"]),
                               "banner":
                               ireplacem(banner_replace_tup, bot["banner"])
                               if bot["banner"] else None,
                }
                    | _user)
                lst.append(bot_obj)
    return lst


async def do_index_query(
    worker_session,
    add_query: str = "",
    state: list = None,
    limit: Optional[int] = 12,
    type: enums.ReviewType = enums.ReviewType.bot,
    **kwargs
) -> List[asyncpg.Record]:
    """
    Performs a 'index' query which can also be used by other things as well
    """
    if state is None:
        state = [0, 6]
    db = worker_session.postgres

    if type == enums.ReviewType.bot:
        table = "bots"
        main_key = "bot_id"
    else:
        table = "servers"
        main_key = "guild_id"

    states = "WHERE " + " OR ".join([f"state = {s}" for s in state])
    base_query = f"SELECT flags, description, banner_card AS banner, state, votes, guild_count, {main_key}, nsfw FROM {table} {states}"
    if limit:
        end_query = f"LIMIT {limit}"
    else:
        end_query = ""
    logger.debug(base_query, add_query, end_query)
    fetch = await db.fetch(" ".join((base_query, add_query, end_query)))
    return await parse_index_query(worker_session, fetch, type=type, **kwargs)
```

**Lightleap DB code (and its reusable here too!)**

```rust
pub async fn index_bots(&self, state: models::State) -> Vec<models::IndexBot> {
    let mut bots: Vec<models::IndexBot> = Vec::new();
    let rows = sqlx::query!(
        "SELECT bot_id, flags, description, banner_card, state, votes, guild_count, nsfw FROM bots WHERE state = $1 ORDER BY votes DESC LIMIT 12",
        state as i32
    )
        .fetch_all(&self.pool)
        .await
        .unwrap();
    for row in rows.iter() {
        let bot = models::IndexBot {
            guild_count: row.guild_count.unwrap_or(0),
            description: row.description.clone().unwrap_or_else(|| "No description set".to_string()),
            banner: row.banner_card.clone().unwrap_or_else(|| "https://api.fateslist.xyz/static/assets/prod/banner.webp".to_string()),
            state: models::State::try_from(row.state).unwrap_or(state),
            nsfw: row.nsfw.unwrap_or(false),
            votes: row.votes.unwrap_or(0),
            flags: row.flags.clone().unwrap_or_default(),
            user: self.get_user(row.bot_id).await,
        };
        bots.push(bot);
    };
    bots
}

pub async fn index_new_bots(&self) -> Vec<models::IndexBot> {
    let mut bots: Vec<models::IndexBot> = Vec::new();
    let rows = sqlx::query!(
        "SELECT bot_id, flags, description, banner_card, state, votes, guild_count, nsfw FROM bots WHERE state = $1 ORDER BY created_at DESC LIMIT 12",
        models::State::Approved as i32
    )
        .fetch_all(&self.pool)
        .await
        .unwrap();
    for row in rows.iter() {
        let bot = models::IndexBot {
            guild_count: row.guild_count.unwrap_or(0),
            description: row.description.clone().unwrap_or_else(|| "No description set".to_string()),
            banner: row.banner_card.clone().unwrap_or_else(|| "https://api.fateslist.xyz/static/assets/prod/banner.webp".to_string()),
            state: models::State::try_from(row.state).unwrap_or(models::State::Approved),
            nsfw: row.nsfw.unwrap_or(false),
            votes: row.votes.unwrap_or(0),
            flags: row.flags.clone().unwrap_or_default(),
            user: self.get_user(row.bot_id).await,
        };
        bots.push(bot);
    };
    bots
}
```

Much cleaner, I could've made this generic and hence decreased size but I wanted the code to be simple and *readable* this time!

**Baypaw:** Why use redis PUBSUB when you could just... use HTTP. Baypaw uses Serenity (next branch) and is far more stable than Flamepaw. Remember the golang IPC code? Here's Baypaw's code:

```rust
#[get("/getch/{id}")]
async fn getch(req: HttpRequest, id: web::Path<u64>) -> HttpResponse {
    let data: &IpcAppData = req.app_data::<web::Data<IpcAppData>>().unwrap();

    let user = data.database.getch(id.into_inner()).await;

    if user.is_some() {
        let user = user.unwrap();
        debug!("Found user {}", user);

        let avatar = user.avatar_url().unwrap_or_else(|| "".to_string());

        return HttpResponse::Ok().json(User {
            username: user.name,
            disc: user.discriminator.to_string(),
            id: user.id.to_string(),
            avatar: avatar,
            status: Status::Unknown,
            bot: user.bot,
        });
    }
    HttpResponse::NotFound().finish()
}

#[derive(Serialize, Deserialize)]
struct Message {
    pub channel_id: u64,
    pub content: String,
    pub embed: serenity::model::channel::Embed,
    pub mention_roles: Vec<String>,
}

#[post("/messages")]
async fn send_message(req: HttpRequest, msg: web::Json<Message>) -> HttpResponse {
    let data: &IpcAppData = req.app_data::<web::Data<IpcAppData>>().unwrap();

    let res = data.database.clis.main.http.send_message(msg.channel_id, &json!({
        "content": msg.content,
        "embeds": vec![msg.embed.clone()],
        "mention_roles": msg.mention_roles,
    })).await;

    if res.is_err() {
        error!("Error sending message: {:?}", res.err());
        return HttpResponse::BadRequest().finish();
    }

    HttpResponse::Ok().finish()
}

#[get("/guild-invite")]
async fn guild_invite(req: HttpRequest, info: web::Query<GuildInviteQuery>) -> HttpResponse {
    let data: &IpcAppData = req.app_data::<web::Data<IpcAppData>>().unwrap();

    if info.cid.clone() != 0 {
        let invite_code = data.database.guild_invite(info.cid, info.uid).await;

        if let Some(url) = invite_code {
            return HttpResponse::Ok().json(GuildInviteData {
                url: url,
                cid: info.cid.clone(),
            });
        }
    } else {
        // First get channels from cache
        let chan_cache = GuildId(info.gid).to_guild_cached(data.database.clis.servers.cache.clone());

        if let Some(guild) = chan_cache {
            let channels = guild.channels;
            for channel in channels.keys() {
                let invite_code = data.database.guild_invite(channel.0, info.uid).await;

                if let Some(url) = invite_code {
                    return HttpResponse::Ok().json(GuildInviteData {
                        url: url,
                        cid: u64::from(channel.0),
                    });
                }
            }
        } else {
            let res = GuildId(info.gid).channels(data.database.clis.servers.http.clone()).await;
            if let Err(err) = res {
                error!("Error getting channels: {:?}", err);
                return HttpResponse::BadRequest().finish();
            }
            let channels = res.unwrap();
            for channel in channels.keys() {
                let invite_code = data.database.guild_invite(channel.0, info.uid).await;

                if let Some(url) = invite_code {
                    return HttpResponse::Ok().json(GuildInviteData {
                        url: url,
                        cid: u64::from(channel.0),
                    });
                }
            }
        }
    }
    HttpResponse::NotFound().finish()
}
```

Much cleaner! It even does more!

### And (truly) finally, Lynx

Lynx was the solution to discordgo not being up to date. Discordgo doesn't even have ``X-Audit-Log-Reason`` support making things almost impossible without a fork! Discordgo also has poor structure compared to other libraries I've seen.

Lynx is the whole admin system that was previously migrated to Flamepaw. Its a web dashboard and it does more than Flamepaw could ever do!

Its written using websockets. Whether this will change depends on how maintainable the current setup is.

With Lynx, the old API docs was moved which will get rid of even more bloated bash scripts!

### And thats a wrap!

**As always, please star our github repo at [https://github.com/Fates-List/infra](https://github.com/Fates-List/infra)**