"""Config for Fates List"""

import json
import os
from typing import Dict, List, Union

with open("config/data/discord.json") as f:
    _discord_data = json.load(f)
    _server_data = _discord_data["servers"]
    _role_data = _discord_data["roles"]
    _channel_data = _discord_data["channels"]
    _oauth_data = _discord_data["oauth"]
    discord_redirect_uri: str = _oauth_data["redirect_uri"]  # Redirect URI
    discord_client_id: int = int(_oauth_data["client_id"])
    owner: int = int(_discord_data["owner"])  # Owner of fates list
    server_bot_invite: str = _discord_data[
        "server_bot_invite"
    ]  # Ensure that it uses 67649 for perms
    support_url: str = _discord_data["support_server"]  # Support server URL
    bot_logs: int = int(_channel_data["bot_logs"])  # Bot logs
    server_logs: int = int(_channel_data["server_logs"])  # Server logs
    appeals_channel: int = int(
        _channel_data["appeals_channel"]
    )  # Appeal/resubmission channel
    site_errors_channel: int = int(
        _channel_data["site_errors_channel"]
    )  # Site error logging
    test_server: int = int(_server_data["testing"])  # Test server
    main_server: int = int(_server_data["main"])  # Main server
    staff_server: int = int(_server_data["staff"])  # Staff server
    staff_ping_add_role: int = int(
        _role_data["staff_ping_add_role"]
    )  # Staff ping role on bot add
    bot_dev_role: int = int(_role_data["bot_dev_role"])  # Bot developer role
    bots_role: int = int(_role_data["bots_role"])  # Bots role on main server
    certified_bots_role: int = int(
        _role_data["certified_bots_role"]
    )  # Certified bots role
    certified_dev_role: int = int(
        _role_data["certified_dev_role"]
    )  # Certified developers role
    bronze_user_role: int = int(
        _role_data["bronze_user_role"]
    )  # Bronze user role in main server
    test_botsrole: int = int(
        _role_data["test_server_bots_role"]
    )  # Test server bots role
    test_staffrole: int = int(
        _role_data["test_server_staff_role"]
    )  # Test server staff role
    staff_ag: int = int(
        _role_data["staff_server_access_granted_role"]
    )  # self-explanatory

with open("config/data/extra_data.json") as f:
    _config_data = json.load(f)
    INT64_MAX: int = int(_config_data["int64_max"])
    API_VERSION: int = _config_data["api_version_curr"]  # Current API version
    # Banned in vanity
    reserved_vanity: List[str] = _config_data["reserved_vanity"]
    md_extensions: List[str] = _config_data[
        "md_extensions"
    ]  # Markdown extension settings
    auth_namespaces: Dict[str, str] = _config_data[
        "auth_namespaces"
    ]  # Deprecated. To remove
    # Badge info.
    special_badges: List[Dict[str, str]] = _config_data["special_badges"]
    features: Dict[str, Dict[str, str]
        ] = _config_data["features"]  # Supported features
    langs: Dict[str, str] = _config_data["langs"]  # Supported langs
    pg_user: str = _config_data[
        "pg_user"
    ]  # Unused (I think) but there for compatibility
    site: str = _config_data["site"]  # Site URL
    sentry_dsn: str = _config_data["sentry_dsn"]

with open("config/data/ban_data.json") as fp:
    bans_data = json.load(fp)

with open("config/data/staff_roles.json") as fp:
    staff_roles = json.load(fp)

with open("config/data/policy.json") as fp:
    _policy_data = json.load(fp)
    rules: Dict[str, List[str]] = _policy_data["rules"]
    privacy_policy: Dict[str, Union[List[str], Dict[str, str]]] = _policy_data[
        "privacy_policy"
    ]
    policies = _policy_data

with open("config/data/secrets.json") as fp:
    _secret_data = json.load(fp)
    TOKEN_SERVER: str = _secret_data["token_server"]
    TOKEN_MANAGER: str = _secret_data["token_manager"]
    patreon_secret: str = _secret_data["patreon_secret"]

with open("config/data/partners.json") as fp:
    partners = json.load(fp)

# Value below should not be changed
site_url = "https://" + site
manager_key = ""  # Backward compatibility
TOKEN_DBG = ""  # Backward compatibility

# Notes
#
# Think about timed badges

TOKEN_MAIN = os.environ["MAIN_TOKEN"]
discord_client_secret = os.environ["CLIENT_SECRET"]
