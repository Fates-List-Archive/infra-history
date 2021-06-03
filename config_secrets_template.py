if not playground:
    TOKEN_MAIN = "" # Main bot token
    TOKEN_SERVER = "" # Main bot token
    oauth_client_secret = "" # OAuth Client Secret
    csrf_secret = "" # CSRF secret
    session_key = "" # Session key
    test_server_manager_key = "" # Test server manager bot (+approve, +claim etc) key
else:
    TOKEN_MAIN = "" # Main bot token
    TOKEN_SERVER = "" # Server token
    oauth_client_secret = "" # Playground
    csrf_secret = "" # Playground
    session_key = "" # Playground
    test_server_manager_key = "" # Public manager key
sentry_dsn = "" # Sentry DNS
pg_pwd = "" # Postgres password
ratelimit_bypass_key = "" # Key for bypassing ratelimit
bb_add_key = "" # Botblock add bot key
bb_edit_key = "" # Botblock edit bot key
test_server_manager_key = "" # Test server manager bot (+approve, +claim etc) key
root_key = "" # This gives almost 100% control over api so keep it safe
rabbitmq_pwd = "" # RabbitMQ password
worker_key = "" # RabbitMQ worker key
