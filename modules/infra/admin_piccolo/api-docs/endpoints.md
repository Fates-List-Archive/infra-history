**API URL**: ``https://next.fateslist.xyz`` *or* ``https://api.fateslist.xyz`` (for now, can change in future)

## Authorization

- **Bot:** These endpoints require a bot token. 
You can get this from Bot Settings. Make sure to keep this safe and in 
a .gitignore/.env. A prefix of `Bot` before the bot token such as 
`Bot abcdef` is supported and can be used to avoid ambiguity but is not 
required. The default auth scheme if no prefix is given depends on the
endpoint: Endpoints which have only one auth scheme will use that auth 
scheme while endpoints with multiple will always use `Bot` for 
backward compatibility

- **Server:** These endpoints require a server
token which you can get using ``/get API Token`` in your server. 
Same warnings and information from the other authentication types 
apply here. A prefix of ``Server`` before the server token is 
supported and can be used to avoid ambiguity but is not required.

- **User:** These endpoints require a user token. You can get this 
from your profile under the User Token section. If you are using this 
for voting, make sure to allow users to opt out! A prefix of `User` 
before the user token such as `User abcdef` is supported and can be 
used to avoid ambiguity but is not required outside of endpoints that 
have both a user and a bot authentication option such as Get Votes. 
In such endpoints, the default will always be a bot auth unless 
you prefix the token with `User`

## Base Response

A default API Response will be of the below format:

```json
{
    "done": true,
    "reason": "Reason for success of failure, can be null",
    "context": "Any extra context"
}
```

## Core

### Post Stats
#### POST /bots/{id}/stats


Post stats to the list

Example:
```py
import requests

# On dpy, guild_count is usually the below
guild_count = len(client.guilds)

# If you are using sharding
shard_count = len(client.shards)
shards = client.shards.keys()

# Optional: User count (this is not accurate for larger bots)
user_count = len(client.users) 

def post_stats(bot_id: int, guild_count: int):
    res = requests.post(f"{api_url}/bots/{bot_id}/stats", json={"guild_count": guild_count})
    json = res.json()
    if res.status != 200:
        # Handle an error in the api
        ...
    return json
```


**API v2 analogue:** (no longer working) [Post Stats](https://legacy.fateslist.xyz/api/docs/redoc#operation/set_stats)

**Path parameters**

- **id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "id": 0
}
```

**Request Body**

```json
{
    "guild_count": 3939,
    "shard_count": 48484,
    "shards": [
        149,
        22020
    ],
    "user_count": 39393
}
```

**Response Body**

```json
{
    "done": false,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [Bot](https://docs.fateslist.xyz/endpoints#authorization)


### Index
#### GET /index

Returns the index for bots and servers

**API v2 analogue:** (no longer working) [Get Index](https://legacy.fateslist.xyz/docs/redoc#operation/get_index)

**Query parameters**

- **target_type** [String? | default = bot (type info may be incomplete, see example)]


**Example**

```json
{
    "target_type": "bot"
}
```

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "new": [
        {
            "guild_count": 0,
            "description": "",
            "banner": "",
            "nsfw": false,
            "votes": 0,
            "state": 0,
            "user": {
                "id": "",
                "username": "",
                "disc": "",
                "avatar": "",
                "bot": false,
                "status": "Unknown"
            },
            "flags": []
        }
    ],
    "top_voted": [
        {
            "guild_count": 0,
            "description": "",
            "banner": "",
            "nsfw": false,
            "votes": 0,
            "state": 0,
            "user": {
                "id": "",
                "username": "",
                "disc": "",
                "avatar": "",
                "bot": false,
                "status": "Unknown"
            },
            "flags": []
        }
    ],
    "certified": [
        {
            "guild_count": 0,
            "description": "",
            "banner": "",
            "nsfw": false,
            "votes": 0,
            "state": 0,
            "user": {
                "id": "",
                "username": "",
                "disc": "",
                "avatar": "",
                "bot": false,
                "status": "Unknown"
            },
            "flags": []
        }
    ],
    "tags": [
        {
            "name": "",
            "iconify_data": "",
            "id": "",
            "owner_guild": null
        }
    ],
    "features": [
        {
            "id": "",
            "name": "",
            "viewed_as": "",
            "description": ""
        }
    ]
}
```
**Authorization Needed** | 


### Resolve Vanity
#### GET /code/{code}

Resolves the vanity for a bot/server in the list

**API v2 analogue:** (no longer working) [Get Vanity](https://legacy.fateslist.xyz/docs/redoc#operation/get_vanity)

**Path parameters**

- **code** [String (type info may be incomplete, see example)]


**Example**

```json
{
    "code": "my-vanity"
}
```

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "target_type": "bot | server",
    "target_id": "0000000000"
}
```
**Authorization Needed** | 


### Get Policies
#### GET /policies

Get policies (rules, privacy policy, terms of service)

**API v2 analogue:** (no longer working) [All Policies](https://legacy.fateslist.xyz/api/docs/redoc#operation/all_policies)

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "rules": {},
    "privacy_policy": {}
}
```
**Authorization Needed** | 


### Get Partners
#### GET /partners

Get policies (rules, privacy policy, terms of service)

**API v2 analogue:** (no longer working) [Get Partners](https://legacy.fateslist.xyz/api/docs/redoc#operation/get_partners)

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "partners": [
        {
            "id": "0",
            "name": "My development",
            "owner": "12345678901234567",
            "image": "",
            "description": "Some random description",
            "links": {
                "discord": "https://discord.com/lmao",
                "website": "https://example.com"
            }
        }
    ],
    "icons": {}
}
```
**Authorization Needed** | 


### Preview Description
#### WS /ws/_preview

Given the preview and long description, parse it and give the sanitized output. You must first connect over websocket!

**API v2 analogue:** None

**Request Body**

```json
{
    "text": "",
    "long_description_type": 1
}
```

**Response Body**

```json
{
    "preview": ""
}
```
**Authorization Needed** | 


### Get Bot
#### GET /bots/{id}


Fetches bot information given a bot ID. If not found, 404 will be returned. 

This endpoint handles both bot IDs and client IDs

Differences from API v2:

- Unlike API v2, this does not support compact or no_cache. Owner order is also guaranteed
- *``long_description/css`` is sanitized with ammonia by default, use `long_description_raw` if you want the unsanitized version*
- All responses are cached for a short period of time. There is *no* way to opt out unlike API v2
- Some fields have been renamed or removed (such as ``promos`` which may be readded at a later date)

This API returns some empty fields such as ``webhook``, ``webhook_secret``, `api_token`` and more. 
This is to allow reuse of the Bot struct in Get Bot Settings which does contain this sensitive data. 

**Set the Frostpaw header if you are a custom client. Send Frostpaw-Invite header on invites**


**API v2 analogue:** [Fetch Bot](https://legacy.fateslist.xyz/docs/redoc#operation/fetch_bot)

**Path parameters**

- **id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "id": 0
}
```

**Query parameters**

- **lang** [Optional <String> (type info may be incomplete, see example)]


**Example**

```json
{
    "lang": null
}
```

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "user": {
        "id": "",
        "username": "",
        "disc": "",
        "avatar": "",
        "bot": false,
        "status": "Unknown"
    },
    "description": "",
    "tags": [],
    "created_at": "1970-01-01T00:00:00Z",
    "last_updated_at": "1970-01-01T00:00:00Z",
    "last_stats_post": "1970-01-01T00:00:00Z",
    "long_description": "blah blah blah",
    "long_description_raw": "blah blah blah unsanitized",
    "long_description_type": 1,
    "guild_count": 0,
    "shard_count": 493,
    "user_count": 0,
    "shards": [],
    "prefix": null,
    "library": "",
    "invite": null,
    "invite_link": "https://discord.com/api/oauth2/authorize....",
    "invite_amount": 48,
    "owners": [
        {
            "user": {
                "id": "",
                "username": "",
                "disc": "",
                "avatar": "",
                "bot": false,
                "status": "Unknown"
            },
            "main": false
        }
    ],
    "owners_html": "",
    "features": [
        {
            "id": "",
            "name": "",
            "viewed_as": "",
            "description": ""
        }
    ],
    "state": 0,
    "page_style": 1,
    "website": null,
    "support": "",
    "github": null,
    "css": "<style></style>",
    "votes": 0,
    "total_votes": 0,
    "vanity": "",
    "donate": null,
    "privacy_policy": null,
    "nsfw": false,
    "banner_card": null,
    "banner_page": null,
    "keep_banner_decor": false,
    "client_id": "",
    "flags": [],
    "action_logs": [
        {
            "user_id": "",
            "bot_id": "",
            "action": 0,
            "action_time": "1970-01-01T00:00:00Z",
            "context": null
        }
    ],
    "vpm": [
        {
            "votes": 0,
            "ts": "1970-01-01T00:00:00Z"
        }
    ],
    "uptime_checks_total": 30,
    "uptime_checks_failed": 19,
    "commands": {
        "default": [
            {
                "cmd_type": 0,
                "groups": [],
                "name": "",
                "vote_locked": false,
                "description": "",
                "args": [],
                "examples": [],
                "premium_only": false,
                "notes": [],
                "doc_link": "",
                "id": null,
                "nsfw": false
            }
        ]
    },
    "resources": [
        {
            "id": null,
            "resource_title": "",
            "resource_link": "",
            "resource_description": ""
        }
    ],
    "webhook": "This will be redacted for Get Bot endpoint",
    "webhook_secret": "This will be redacted for Get Bot endpoint",
    "webhook_type": null,
    "webhook_hmac_only": null,
    "api_token": "This will be redacted for Get Bot endpoint"
}
```
**Authorization Needed** | 


### Search List
#### GET /search?q={query}

Searches the list based on a query named ``q``

**API v2 analogue:** (no longer working) [Search List](https://legacy.fateslist.xyz/docs/redoc#operation/search_list)

**Query parameters**

- **q** [String? | default = mew (type info may be incomplete, see example)]


**Example**

```json
{
    "q": "mew"
}
```

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "bots": [
        {
            "guild_count": 0,
            "description": "",
            "banner": "",
            "nsfw": false,
            "votes": 0,
            "state": 0,
            "user": {
                "id": "",
                "username": "",
                "disc": "",
                "avatar": "",
                "bot": false,
                "status": "Unknown"
            },
            "flags": []
        }
    ],
    "servers": [
        {
            "guild_count": 0,
            "description": "",
            "banner": "",
            "nsfw": false,
            "votes": 0,
            "state": 0,
            "user": {
                "id": "",
                "username": "",
                "disc": "",
                "avatar": "",
                "bot": false,
                "status": "Unknown"
            },
            "flags": []
        }
    ],
    "profiles": [
        {
            "banner": "",
            "description": "",
            "user": {
                "id": "",
                "username": "",
                "disc": "",
                "avatar": "",
                "bot": false,
                "status": "Unknown"
            }
        }
    ],
    "packs": [
        {
            "id": "0",
            "name": "",
            "description": "",
            "icon": "",
            "banner": "",
            "resolved_bots": [
                {
                    "user": {
                        "id": "",
                        "username": "",
                        "disc": "",
                        "avatar": "",
                        "bot": false,
                        "status": "Unknown"
                    },
                    "description": ""
                }
            ],
            "owner": {
                "id": "",
                "username": "",
                "disc": "",
                "avatar": "",
                "bot": false,
                "status": "Unknown"
            },
            "created_at": "1970-01-01T00:00:00Z"
        }
    ],
    "tags": {
        "bots": [
            {
                "name": "",
                "iconify_data": "",
                "id": "",
                "owner_guild": null
            }
        ],
        "servers": [
            {
                "name": "",
                "iconify_data": "",
                "id": "",
                "owner_guild": null
            }
        ]
    }
}
```
**Authorization Needed** | 


### Search Tag
#### GET /search-tags?q={query}

Searches the list for all bots/servers with tag *exactly* specified ``q``

**API v2 analogue:** (no longer working) [Search List](https://legacy.fateslist.xyz/docs/redoc#operation/search_list)

**Query parameters**

- **q** [String? | default = music (type info may be incomplete, see example)]


**Example**

```json
{
    "q": "music"
}
```

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "bots": [
        {
            "guild_count": 0,
            "description": "",
            "banner": "",
            "nsfw": false,
            "votes": 0,
            "state": 0,
            "user": {
                "id": "",
                "username": "",
                "disc": "",
                "avatar": "",
                "bot": false,
                "status": "Unknown"
            },
            "flags": []
        }
    ],
    "servers": [
        {
            "guild_count": 0,
            "description": "",
            "banner": "",
            "nsfw": false,
            "votes": 0,
            "state": 0,
            "user": {
                "id": "",
                "username": "",
                "disc": "",
                "avatar": "",
                "bot": false,
                "status": "Unknown"
            },
            "flags": []
        }
    ],
    "profiles": [],
    "packs": [],
    "tags": {
        "bots": [
            {
                "name": "",
                "iconify_data": "",
                "id": "",
                "owner_guild": null
            }
        ],
        "servers": [
            {
                "name": "",
                "iconify_data": "",
                "id": "",
                "owner_guild": null
            }
        ]
    }
}
```
**Authorization Needed** | 


### Random Bot
#### GET /random-bot


Fetches a random bot on the list

Example:
```py
import requests

def random_bot():
    res = requests.get(api_url"/random-bot")
    json = res.json()
    if res.status != 200:
        # Handle an error in the api
        ...
    return json
```


**API v2 analogue:** (no longer working) [Fetch Random Bot](https://legacy.fateslist.xyz/api/docs/redoc#operation/fetch_random_bot)

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "guild_count": 0,
    "description": "",
    "banner": "",
    "nsfw": false,
    "votes": 0,
    "state": 0,
    "user": {
        "id": "",
        "username": "",
        "disc": "",
        "avatar": "",
        "bot": false,
        "status": "Unknown"
    },
    "flags": []
}
```
**Authorization Needed** | 


### Random Server
#### GET /random-server


Fetches a random server on the list

Example:
```py
import requests

def random_server():
    res = requests.get(api_url"/random-server")
    json = res.json()
    if res.status != 200:
        # Handle an error in the api
        ...
    return json
```


**API v2 analogue:** (no longer working) [Fetch Random Server](https://legacy.fateslist.xyz/api/docs/redoc#operation/fetch_random_server)

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "guild_count": 0,
    "description": "",
    "banner": "",
    "nsfw": false,
    "votes": 0,
    "state": 0,
    "user": {
        "id": "",
        "username": "",
        "disc": "",
        "avatar": "",
        "bot": false,
        "status": "Unknown"
    },
    "flags": []
}
```
**Authorization Needed** | 


### Get Server
#### GET /servers/{id}


Fetches server information given a server/guild ID. If not found, 404 will be returned. 

Differences from API v2:

- Unlike API v2, this does not support compact or no_cache.
- *``long_description/css`` is sanitized with ammonia by default, use `long_description_raw` if you want the unsanitized version*
- All responses are cached for a short period of time. There is *no* way to opt out unlike API v2
- Some fields have been renamed or removed
- ``invite_link`` is returned, however is always None unless ``Frostpaw-Invite`` header is set which then pushes you into 
server privacy restrictions

**Set the Frostpaw header if you are a custom client**


**API v2 analogue:** (no longer working) [Fetch Server](https://legacy.fateslist.xyz/docs/redoc#operation/fetch_server)

**Path parameters**

- **id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "id": 0
}
```

**Query parameters**

- **lang** [Optional <String> (type info may be incomplete, see example)]


**Example**

```json
{
    "lang": null
}
```

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "user": {
        "id": "",
        "username": "",
        "disc": "",
        "avatar": "",
        "bot": false,
        "status": "Unknown"
    },
    "description": "",
    "tags": [],
    "long_description_type": 1,
    "long_description": "",
    "long_description_raw": "",
    "vanity": null,
    "guild_count": 0,
    "invite_amount": 0,
    "invite_link": null,
    "created_at": "1970-01-01T00:00:00Z",
    "state": 0,
    "flags": [],
    "css": "",
    "website": null,
    "banner_card": null,
    "banner_page": null,
    "keep_banner_decor": false,
    "nsfw": false,
    "votes": 0,
    "total_votes": 0
}
```
**Authorization Needed** | 


### Get User Votes
#### GET /users/{user_id}/bots/{bot_id}/votes


Endpoint to check amount of votes a user has.

- votes | The amount of votes the bot has.
- voted | Whether or not the user has *ever* voted for the bot.
- vote_epoch | The redis TTL of the users vote lock. This is not time_to_vote which is the
elapsed time the user has waited since their last vote.
- timestamps | A list of timestamps that the user has voted for the bot on that has been recorded.
- time_to_vote | The time the user has waited since they last voted.
- vote_right_now | Whether a user can vote right now. Currently equivalent to `vote_epoch < 0`.

Differences from API v2:

- Unlike API v2, this does not require authorization to use. This is to speed up responses and 
because the last thing people want to scrape are Fates List user votes anyways. **You should not rely on
this however, it is prone to change *anytime* in the future**.
- ``vts`` has been renamed to ``timestamps``


**API v2 analogue:** (no longer working) [Get User Votes](https://legacy.fateslist.xyz/api/docs/redoc#operation/get_user_votes)

**Path parameters**

- **user_id** [i64 (type info may be incomplete, see example)]
- **bot_id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "user_id": 0,
    "bot_id": 0
}
```

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "votes": 10,
    "voted": true,
    "vote_right_now": false,
    "vote_epoch": 101,
    "time_to_vote": 0,
    "timestamps": [
        "1970-01-01T00:00:00Z"
    ]
}
```
**Authorization Needed** | 


### Create User Vote
#### PATCH /users/{user_id}/bots/{bot_id}/votes


This endpoint creates a vote for a bot which can only be done *once* every 8 hours.

**It is documented purely to enable staff to use it**


**API v2 analogue:** None

**Path parameters**

- **user_id** [i64 (type info may be incomplete, see example)]
- **bot_id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "user_id": 0,
    "bot_id": 0
}
```

**Query parameters**

- **test** [bool (type info may be incomplete, see example)]


**Example**

```json
{
    "test": true
}
```

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "done": false,
    "reason": "Why the vote failed",
    "context": null
}
```
**Authorization Needed** | [User](https://docs.fateslist.xyz/endpoints#authorization)


### Mini Index
#### GET /mini-index


Returns a mini-index which is basically a Index but with only ``tags``
and ``features`` having any data. Other fields are empty arrays/vectors.

This is used internally by sunbeam for the add bot system where a full bot
index is too costly and making a new struct is unnecessary.


**API v2 analogue:** None

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "new": [],
    "top_voted": [],
    "certified": [],
    "tags": [
        {
            "name": "",
            "iconify_data": "",
            "id": "",
            "owner_guild": null
        }
    ],
    "features": [
        {
            "id": "",
            "name": "",
            "viewed_as": "",
            "description": ""
        }
    ]
}
```
**Authorization Needed** | 


### Gets Bot Settings
#### GET /users/{user_id}/bots/{bot_id}/settings


Returns the bot settings.

The ``bot`` key here is equivalent to a Get Bot response with the following
differences:

- Sensitive fields (see examples) like ``webhook``, ``api_token``, 
``webhook_secret`` and others are filled out here
- This API only allows bot owners to use it, otherwise it will 400!

Staff members *should* instead use Lynx.

Due to massive changes, this API cannot be mapped onto any v2 API


**API v2 analogue:** None

**Path parameters**

- **user_id** [i64 (type info may be incomplete, see example)]
- **bot_id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "user_id": 0,
    "bot_id": 0
}
```

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "bot": {
        "user": {
            "id": "",
            "username": "",
            "disc": "",
            "avatar": "",
            "bot": false,
            "status": "Unknown"
        },
        "description": "",
        "tags": [],
        "created_at": "1970-01-01T00:00:00Z",
        "last_updated_at": "1970-01-01T00:00:00Z",
        "last_stats_post": "1970-01-01T00:00:00Z",
        "long_description": "blah blah blah",
        "long_description_raw": "blah blah blah unsanitized",
        "long_description_type": 1,
        "guild_count": 0,
        "shard_count": 493,
        "user_count": 0,
        "shards": [],
        "prefix": null,
        "library": "",
        "invite": null,
        "invite_link": "https://discord.com/api/oauth2/authorize....",
        "invite_amount": 48,
        "owners": [
            {
                "user": {
                    "id": "",
                    "username": "",
                    "disc": "",
                    "avatar": "",
                    "bot": false,
                    "status": "Unknown"
                },
                "main": false
            }
        ],
        "owners_html": "",
        "features": [
            {
                "id": "",
                "name": "",
                "viewed_as": "",
                "description": ""
            }
        ],
        "state": 0,
        "page_style": 1,
        "website": null,
        "support": "",
        "github": null,
        "css": "<style></style>",
        "votes": 0,
        "total_votes": 0,
        "vanity": "",
        "donate": null,
        "privacy_policy": null,
        "nsfw": false,
        "banner_card": null,
        "banner_page": null,
        "keep_banner_decor": false,
        "client_id": "",
        "flags": [],
        "action_logs": [
            {
                "user_id": "",
                "bot_id": "",
                "action": 0,
                "action_time": "1970-01-01T00:00:00Z",
                "context": null
            }
        ],
        "vpm": [
            {
                "votes": 0,
                "ts": "1970-01-01T00:00:00Z"
            }
        ],
        "uptime_checks_total": 30,
        "uptime_checks_failed": 19,
        "commands": {
            "default": [
                {
                    "cmd_type": 0,
                    "groups": [],
                    "name": "",
                    "vote_locked": false,
                    "description": "",
                    "args": [],
                    "examples": [],
                    "premium_only": false,
                    "notes": [],
                    "doc_link": "",
                    "id": null,
                    "nsfw": false
                }
            ]
        },
        "resources": [
            {
                "id": null,
                "resource_title": "",
                "resource_link": "",
                "resource_description": ""
            }
        ],
        "webhook": "This will be redacted for Get Bot endpoint",
        "webhook_secret": "This will be redacted for Get Bot endpoint",
        "webhook_type": null,
        "webhook_hmac_only": null,
        "api_token": "This will be redacted for Get Bot endpoint"
    },
    "context": {
        "tags": [
            {
                "name": "",
                "iconify_data": "",
                "id": "",
                "owner_guild": null
            }
        ],
        "features": [
            {
                "id": "",
                "name": "",
                "viewed_as": "",
                "description": ""
            }
        ]
    }
}
```
**Authorization Needed** | [User](https://docs.fateslist.xyz/endpoints#authorization)


## Auth

### Get OAuth2 Link
#### GET /oauth2

Returns the oauth2 link used to login with

**API v2 analogue:** (no longer working) [Get OAuth2 Link](https://legacy.fateslist.xyz/docs/redoc#operation/get_oauth2_link)

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": "https://discord.com/........."
}
```
**Authorization Needed** | 


### Create OAuth2 Login
#### POST /oauth2

Creates a oauth2 login given a code

**API v2 analogue:** (no longer working) [Login User](https://legacy.fateslist.xyz/api/docs/redoc#operation/login_user)

**Request Body**

```json
{
    "code": "code from discord oauth",
    "state": "Random UUID right now"
}
```

**Response Body**

```json
{
    "state": 0,
    "token": "",
    "user": {
        "id": "",
        "username": "",
        "disc": "",
        "avatar": "",
        "bot": false,
        "status": "Unknown"
    },
    "site_lang": "",
    "css": null
}
```
**Authorization Needed** | 


### Delete OAuth2 Login
#### DELETE /oauth2


'Deletes' (logs out) a oauth2 login. Always call this when logging out 
even if you do not use cookies as it may perform other logout tasks in future

This API is essentially a logout


**API v2 analogue:** (no longer working) [Logout Sunbeam](https://legacy.fateslist.xyz/docs/redoc#operation/logout_sunbeam)

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | 


## Security

### New Bot Token
#### DELETE /bots/{id}/token


'Deletes' a bot token and reissues a new bot token. Use this if your bots
token ever gets leaked.


**API v2 analogue:** None

**Path parameters**

- **id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "id": 0
}
```

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [Bot](https://docs.fateslist.xyz/endpoints#authorization)


### New User Token
#### DELETE /users/{id}/token


'Deletes' a user token and reissues a new user token. Use this if your user
token ever gets leaked.


**API v2 analogue:** None

**Path parameters**

- **id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "id": 0
}
```

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://docs.fateslist.xyz/endpoints#authorization)


### New Server Token
#### DELETE /servers/{id}/token


'Deletes' a server token and reissues a new server token. Use this if your server
token ever gets leaked.


**API v2 analogue:** None

**Path parameters**

- **id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "id": 0
}
```

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [Server](https://docs.fateslist.xyz/endpoints#authorization)


## Bot Actions

### New Bot
#### POST /users/{id}/bots


Creates a new bot. 

Set ``created_at``, ``last_stats_post`` to sometime in the past

Set ``api_token``, ``guild_count`` etc (unknown/not editable fields) to any 
random value of the same type

With regards to ``extra_owners``, put all of them as a ``BotOwner`` object
containing ``main`` set to ``false`` and ``user`` as a dummy ``user`` object 
containing ``id`` filled in and the rest of a ``user``empty strings. Set ``bot``
to false.


**API v2 analogue:** None

**Path parameters**

- **id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "id": 0
}
```

**Request Body**

```json
{
    "user": {
        "id": "",
        "username": "",
        "disc": "",
        "avatar": "",
        "bot": false,
        "status": "Unknown"
    },
    "description": "",
    "tags": [],
    "created_at": "1970-01-01T00:00:00Z",
    "last_updated_at": "1970-01-01T00:00:00Z",
    "last_stats_post": "1970-01-01T00:00:00Z",
    "long_description": "blah blah blah",
    "long_description_raw": "blah blah blah unsanitized",
    "long_description_type": 1,
    "guild_count": 0,
    "shard_count": 493,
    "user_count": 0,
    "shards": [],
    "prefix": null,
    "library": "",
    "invite": null,
    "invite_link": "https://discord.com/api/oauth2/authorize....",
    "invite_amount": 48,
    "owners": [
        {
            "user": {
                "id": "",
                "username": "",
                "disc": "",
                "avatar": "",
                "bot": false,
                "status": "Unknown"
            },
            "main": false
        }
    ],
    "owners_html": "",
    "features": [
        {
            "id": "",
            "name": "",
            "viewed_as": "",
            "description": ""
        }
    ],
    "state": 0,
    "page_style": 1,
    "website": null,
    "support": "",
    "github": null,
    "css": "<style></style>",
    "votes": 0,
    "total_votes": 0,
    "vanity": "",
    "donate": null,
    "privacy_policy": null,
    "nsfw": false,
    "banner_card": null,
    "banner_page": null,
    "keep_banner_decor": false,
    "client_id": "",
    "flags": [],
    "action_logs": [
        {
            "user_id": "",
            "bot_id": "",
            "action": 0,
            "action_time": "1970-01-01T00:00:00Z",
            "context": null
        }
    ],
    "vpm": [
        {
            "votes": 0,
            "ts": "1970-01-01T00:00:00Z"
        }
    ],
    "uptime_checks_total": 30,
    "uptime_checks_failed": 19,
    "commands": {
        "default": [
            {
                "cmd_type": 0,
                "groups": [],
                "name": "",
                "vote_locked": false,
                "description": "",
                "args": [],
                "examples": [],
                "premium_only": false,
                "notes": [],
                "doc_link": "",
                "id": null,
                "nsfw": false
            }
        ]
    },
    "resources": [
        {
            "id": null,
            "resource_title": "",
            "resource_link": "",
            "resource_description": ""
        }
    ],
    "webhook": "This will be redacted for Get Bot endpoint",
    "webhook_secret": "This will be redacted for Get Bot endpoint",
    "webhook_type": null,
    "webhook_hmac_only": null,
    "api_token": "This will be redacted for Get Bot endpoint"
}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://docs.fateslist.xyz/endpoints#authorization)


### Edit Bot
#### PATCH /users/{id}/bots


Edits a existing bot. 

Set ``created_at``, ``last_stats_post`` to sometime in the past

Set ``api_token``, ``guild_count`` etc (unknown/not editable fields) to any 
random value of the same type

With regards to ``extra_owners``, put all of them as a ``BotOwner`` object
containing ``main`` set to ``false`` and ``user`` as a dummy ``user`` object 
containing ``id`` filled in and the rest of a ``user``empty strings. Set ``bot``
to false.


**API v2 analogue:** None

**Path parameters**

- **id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "id": 0
}
```

**Request Body**

```json
{
    "user": {
        "id": "",
        "username": "",
        "disc": "",
        "avatar": "",
        "bot": false,
        "status": "Unknown"
    },
    "description": "",
    "tags": [],
    "created_at": "1970-01-01T00:00:00Z",
    "last_updated_at": "1970-01-01T00:00:00Z",
    "last_stats_post": "1970-01-01T00:00:00Z",
    "long_description": "blah blah blah",
    "long_description_raw": "blah blah blah unsanitized",
    "long_description_type": 1,
    "guild_count": 0,
    "shard_count": 493,
    "user_count": 0,
    "shards": [],
    "prefix": null,
    "library": "",
    "invite": null,
    "invite_link": "https://discord.com/api/oauth2/authorize....",
    "invite_amount": 48,
    "owners": [
        {
            "user": {
                "id": "",
                "username": "",
                "disc": "",
                "avatar": "",
                "bot": false,
                "status": "Unknown"
            },
            "main": false
        }
    ],
    "owners_html": "",
    "features": [
        {
            "id": "",
            "name": "",
            "viewed_as": "",
            "description": ""
        }
    ],
    "state": 0,
    "page_style": 1,
    "website": null,
    "support": "",
    "github": null,
    "css": "<style></style>",
    "votes": 0,
    "total_votes": 0,
    "vanity": "",
    "donate": null,
    "privacy_policy": null,
    "nsfw": false,
    "banner_card": null,
    "banner_page": null,
    "keep_banner_decor": false,
    "client_id": "",
    "flags": [],
    "action_logs": [
        {
            "user_id": "",
            "bot_id": "",
            "action": 0,
            "action_time": "1970-01-01T00:00:00Z",
            "context": null
        }
    ],
    "vpm": [
        {
            "votes": 0,
            "ts": "1970-01-01T00:00:00Z"
        }
    ],
    "uptime_checks_total": 30,
    "uptime_checks_failed": 19,
    "commands": {
        "default": [
            {
                "cmd_type": 0,
                "groups": [],
                "name": "",
                "vote_locked": false,
                "description": "",
                "args": [],
                "examples": [],
                "premium_only": false,
                "notes": [],
                "doc_link": "",
                "id": null,
                "nsfw": false
            }
        ]
    },
    "resources": [
        {
            "id": null,
            "resource_title": "",
            "resource_link": "",
            "resource_description": ""
        }
    ],
    "webhook": "This will be redacted for Get Bot endpoint",
    "webhook_secret": "This will be redacted for Get Bot endpoint",
    "webhook_type": null,
    "webhook_hmac_only": null,
    "api_token": "This will be redacted for Get Bot endpoint"
}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://docs.fateslist.xyz/endpoints#authorization)


### Transfer Ownership
#### PATCH /users/{user_id}/bots/{bot_id}/main-owner


Transfers bot ownership.

You **must** be main owner to use this endpoint.


**API v2 analogue:** None

**Path parameters**

- **user_id** [i64 (type info may be incomplete, see example)]
- **bot_id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "user_id": 0,
    "bot_id": 0
}
```

**Request Body**

```json
{
    "user": {
        "id": "id here",
        "username": "Leave blank",
        "disc": "Leave blank",
        "avatar": "Leave blank",
        "bot": false,
        "status": "Unknown"
    },
    "main": true
}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://docs.fateslist.xyz/endpoints#authorization)


### Delete Bot
#### DELETE /users/{user_id}/bots/{bot_id}


Deletes a bot.

You **must** be main owner to use this endpoint.


**API v2 analogue:** None

**Path parameters**

- **user_id** [i64 (type info may be incomplete, see example)]
- **bot_id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "user_id": 0,
    "bot_id": 0
}
```

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://docs.fateslist.xyz/endpoints#authorization)


## Appeal

### New Appeal
#### POST /users/{user_id}/bots/{bot_id}/appeal


Creates a appeal/request for a bot.

``request_type`` is a ``BotRequestType``, see [Enum Reference](https://docs.fateslist.xyz/structures/enums.autogen/)

**Ideally should only be used for custom clients**


**API v2 analogue:** None

**Path parameters**

- **user_id** [i64 (type info may be incomplete, see example)]
- **bot_id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "user_id": 0,
    "bot_id": 0
}
```

**Request Body**

```json
{
    "request_type": 0,
    "appeal": "This bot deserves to be unbanned because..."
}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://docs.fateslist.xyz/endpoints#authorization)


## Packs

### Add Pack
#### GET /users/{id}/packs


Creates a bot pack. 

- Set ``id`` to empty string, 
- Set ``created_at`` to any datetime
- In user and bot, only ``id`` must be filled, all others can be left empty string
but must exist in the object


**API v2 analogue:** None

**Request Body**

```json
{
    "id": "0",
    "name": "",
    "description": "",
    "icon": "",
    "banner": "",
    "resolved_bots": [
        {
            "user": {
                "id": "",
                "username": "",
                "disc": "",
                "avatar": "",
                "bot": false,
                "status": "Unknown"
            },
            "description": ""
        }
    ],
    "owner": {
        "id": "",
        "username": "",
        "disc": "",
        "avatar": "",
        "bot": false,
        "status": "Unknown"
    },
    "created_at": "1970-01-01T00:00:00Z"
}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://docs.fateslist.xyz/endpoints#authorization)


## Users

### Get Profile
#### GET /profiles/{id}


Gets a user profile.


**API v2 analogue:** None

**Path parameters**

- **id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "id": 0
}
```

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "user": {
        "id": "",
        "username": "",
        "disc": "",
        "avatar": "",
        "bot": false,
        "status": "Unknown"
    },
    "bots": [],
    "description": "",
    "profile_css": "",
    "user_css": "",
    "vote_reminder_channel": null,
    "packs": [],
    "state": 0,
    "site_lang": "",
    "action_logs": []
}
```
**Authorization Needed** | 


### Edit Profile
#### PATCH /profiles/{id}


Edits a user profile.

``user`` can be completely empty valued but the keys present in a User must
be present


**API v2 analogue:** None

**Path parameters**

- **id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "id": 0
}
```

**Request Body**

```json
{
    "user": {
        "id": "",
        "username": "",
        "disc": "",
        "avatar": "",
        "bot": false,
        "status": "Unknown"
    },
    "bots": [],
    "description": "",
    "profile_css": "",
    "user_css": "",
    "vote_reminder_channel": null,
    "packs": [],
    "state": 0,
    "site_lang": "",
    "action_logs": []
}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | 


## Reviews

### Get Reviews
#### GET /reviews/{id}


Gets reviews for a reviewable entity.

A reviewable entity is currently only a bot or a server. Profile reviews are a possibility
in the future.

A bot has a TargetType of 0 while a server has a TargetType of 1. This is the ``target_type``

This reviewable entities id which is a ``i64`` is the id that is specifed in the
path.

``page`` must be greater than 0 or omitted (which will default to page 1).

``user_id`` is optional for this endpoint but specifying it will provide ``user_reviews`` if
the user has made a review. This will tell you the users review for the entity.

``per_page`` (amount of root/non-reply reviews per page) is currently set to 9. 
This may change in the future and is given by ``per_page`` key.

``from`` contains the index/count of the first review of the page.


**API v2 analogue:** None

**Path parameters**

- **id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "id": 0
}
```

**Query parameters**

- **target_type** [fates::models::TargetType (type info may be incomplete, see example)]
- **page** [Optional <i32> (type info may be incomplete, see example)]
- **user_id** [i64? | default = 0 (type info may be incomplete, see example)]


**Example**

```json
{
    "target_type": 0,
    "page": 1,
    "user_id": 0
}
```

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "reviews": [
        {
            "id": null,
            "reply": false,
            "star_rating": "0",
            "review_text": "",
            "votes": {
                "votes": [],
                "upvotes": [],
                "downvotes": []
            },
            "flagged": false,
            "user": {
                "id": "",
                "username": "",
                "disc": "",
                "avatar": "",
                "bot": false,
                "status": "Unknown"
            },
            "epoch": [],
            "replies": [],
            "parent_id": null
        }
    ],
    "per_page": 9,
    "from": 0,
    "stats": {
        "average_stars": "8.800000",
        "total": 78
    },
    "user_review": {
        "id": null,
        "reply": false,
        "star_rating": "0",
        "review_text": "",
        "votes": {
            "votes": [],
            "upvotes": [],
            "downvotes": []
        },
        "flagged": false,
        "user": {
            "id": "",
            "username": "",
            "disc": "",
            "avatar": "",
            "bot": false,
            "status": "Unknown"
        },
        "epoch": [],
        "replies": [],
        "parent_id": null
    }
}
```
**Authorization Needed** | 


### Create Review
#### POST /reviews/{id}


Creates a review.

``id`` and ``page`` should be set to null or omitted though are ignored by this endpoint
so there should not be an error even if provided.

A reviewable entity is currently only a bot or a server. Profile reviews are a possibility
in the future.

A bot has a TargetType of 0 while a server has a TargetType of 1. This is the ``target_type``

This reviewable entities id which is a ``i64`` is the id that is specifed in the
path.

``user_id`` is *required* for this endpoint and must be the user making the review. It must
also match the user token sent in the ``Authorization`` header


**API v2 analogue:** None

**Path parameters**

- **id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "id": 0
}
```

**Query parameters**

- **target_type** [fates::models::TargetType (type info may be incomplete, see example)]
- **page** [Optional <i32> (type info may be incomplete, see example)]
- **user_id** [i64? | default = 0 (type info may be incomplete, see example)]


**Example**

```json
{
    "target_type": 0,
    "page": null,
    "user_id": 0
}
```

**Request Body**

```json
{
    "id": null,
    "reply": false,
    "star_rating": "0",
    "review_text": "",
    "votes": {
        "votes": [],
        "upvotes": [],
        "downvotes": []
    },
    "flagged": false,
    "user": {
        "id": "",
        "username": "",
        "disc": "",
        "avatar": "",
        "bot": false,
        "status": "Unknown"
    },
    "epoch": [],
    "replies": [],
    "parent_id": null
}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://docs.fateslist.xyz/endpoints#authorization)


### Edit Review
#### PATCH /reviews/{id}


Edits a review.

``page`` should be set to null or omitted though are ignored by this endpoint
so there should not be an error even if provided.

A reviewable entity is currently only a bot or a server. Profile reviews are a possibility
in the future.

A bot has a TargetType of 0 while a server has a TargetType of 1. This is the ``target_type``

This reviewable entities id which is a ``i64`` is the id that is specifed in the
path.

The id of the review must be specified as ``id`` in the request body which accepts a ``Review``
object. The ``user_id`` specified must *own*/have created the review being editted. Staff should
edit reviews using Lynx when required.

``user_id`` is *required* for this endpoint and must be the user making the review. It must
also match the user token sent in the ``Authorization`` header


**API v2 analogue:** None

**Path parameters**

- **id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "id": 0
}
```

**Query parameters**

- **target_type** [fates::models::TargetType (type info may be incomplete, see example)]
- **page** [Optional <i32> (type info may be incomplete, see example)]
- **user_id** [i64? | default = 0 (type info may be incomplete, see example)]


**Example**

```json
{
    "target_type": 0,
    "page": null,
    "user_id": 0
}
```

**Request Body**

```json
{
    "id": "d9f7a209-20a8-40a5-9958-1d1e82a641fc",
    "reply": false,
    "star_rating": "0",
    "review_text": "",
    "votes": {
        "votes": [],
        "upvotes": [],
        "downvotes": []
    },
    "flagged": false,
    "user": {
        "id": "",
        "username": "",
        "disc": "",
        "avatar": "",
        "bot": false,
        "status": "Unknown"
    },
    "epoch": [],
    "replies": [],
    "parent_id": null
}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://docs.fateslist.xyz/endpoints#authorization)


### Delete Review
#### DELETE /reviews/{rid}


Deletes a review

``rid`` must be a valid uuid.

``user_id`` is *required* for this endpoint and must be the user making the review. It must
also match the user token sent in the ``Authorization`` header

A reviewable entity is currently only a bot or a server. Profile reviews are a possibility
in the future.

A bot has a TargetType of 0 while a server has a TargetType of 1. This is the ``target_type``

``target_type`` is not currently checked but it is a good idea to set it anyways. You must
set this a TargetType anyways so you might as well set it correctly.


**API v2 analogue:** None

**Path parameters**

- **rid** [String (type info may be incomplete, see example)]


**Example**

```json
{
    "rid": "5a0cd147-0d02-4664-a5ee-b1c5836de959"
}
```

**Query parameters**

- **target_type** [fates::models::TargetType (type info may be incomplete, see example)]
- **page** [Optional <i32> (type info may be incomplete, see example)]
- **user_id** [i64? | default = 0 (type info may be incomplete, see example)]


**Example**

```json
{
    "target_type": 0,
    "page": null,
    "user_id": 0
}
```

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://docs.fateslist.xyz/endpoints#authorization)


### Vote Review
#### PATCH /reviews/{rid}/votes


Creates a vote for a review

``rid`` must be a valid uuid.

``user_id`` is *required* for this endpoint and must be the user making the review. It must
also match the user token sent in the ``Authorization`` header. 

**Unlike other review APIs, ``user_id`` here is in request body as ReviewVote object**

A reviewable entity is currently only a bot or a server. Profile reviews are a possibility
in the future.

A bot has a TargetType of 0 while a server has a TargetType of 1. This is the ``target_type``

**This endpoint does not require ``target_type`` at all. You can safely omit it**


**API v2 analogue:** None

**Path parameters**

- **rid** [String (type info may be incomplete, see example)]


**Example**

```json
{
    "rid": "7c5f7b1b-2545-4df8-b065-ed200d03bdcd"
}
```

**Request Body**

```json
{
    "user_id": "user id here",
    "upvote": true
}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://docs.fateslist.xyz/endpoints#authorization)


## Stats

### Get List Stats
#### GET /stats


Returns the bot list stats. This currently returns the full list of all bots
as a vector/list of IndexBot structs.

As a client, it is your responsibility, to parse this. Pagination may be added
if the list grows and then requires it.


**API v2 analogue:** None

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "total_bots": 0,
    "total_servers": 0,
    "total_users": 0,
    "bots": [
        {
            "guild_count": 0,
            "description": "",
            "banner": "",
            "nsfw": false,
            "votes": 0,
            "state": 0,
            "user": {
                "id": "",
                "username": "",
                "disc": "",
                "avatar": "",
                "bot": false,
                "status": "Unknown"
            },
            "flags": []
        }
    ],
    "servers": [],
    "uptime": 0.0,
    "cpu_idle": 0.0,
    "mem_total": 0,
    "mem_free": 0,
    "mem_available": 0,
    "swap_total": 0,
    "swap_free": 0,
    "mem_dirty": 0,
    "mem_active": 0,
    "mem_inactive": 0,
    "mem_buffers": 0,
    "mem_committed": 0
}
```
**Authorization Needed** | 


## Resources

### Create Resource
#### POST /resources/{id}


Creates a resource. Both bots and servers support these however only bots 
support the frontend resource creator in Bot Settings as of right now.

The ``id`` here must be the resource id

A bot has a TargetType of 0 while a server has a TargetType of 1. 
This is the ``target_type``


**API v2 analogue:** None

**Path parameters**

- **id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "id": 0
}
```

**Query parameters**

- **target_type** [fates::models::TargetType (type info may be incomplete, see example)]


**Example**

```json
{
    "target_type": 0
}
```

**Request Body**

```json
{
    "id": null,
    "resource_title": "",
    "resource_link": "",
    "resource_description": ""
}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [Bot](https://docs.fateslist.xyz/endpoints#authorization), [Server](https://docs.fateslist.xyz/endpoints#authorization)


### Delete Resource
#### DELETE /resources/{id}


Deletes a resource. Both bots and servers support these however only bots 
support the frontend resource creator in Bot Settings as of right now.

The ``id`` here must be the resource id

A bot has a TargetType of 0 while a server has a TargetType of 1. 
This is the ``target_type``


**API v2 analogue:** None

**Path parameters**

- **id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "id": 0
}
```

**Query parameters**

- **id** [String (type info may be incomplete, see example)]
- **target_type** [fates::models::TargetType (type info may be incomplete, see example)]


**Example**

```json
{
    "id": "48b7b682-18aa-46fb-afc8-88e08ab2dea5",
    "target_type": 0
}
```

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [Bot](https://docs.fateslist.xyz/endpoints#authorization), [Server](https://docs.fateslist.xyz/endpoints#authorization)


## Commands

### Create Bot Command
#### POST /bots/{id}/commands


Creates a command.

The ``id`` here must be the bot id you wish to add the command for

**This performs a *upsert* meaning it will either create or update 
the command depending on its ``name``.**

**Only post up to 10-20 commands at a time, otherwise requests may be truncated
or otherwise fail with odd errors.  If you have more than this, then perform 
multiple requests**


**API v2 analogue:** None

**Path parameters**

- **id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "id": 0
}
```

**Query parameters**

- **target_type** [fates::models::TargetType (type info may be incomplete, see example)]


**Example**

```json
{
    "target_type": 0
}
```

**Request Body**

```json
{
    "commands": [
        {
            "cmd_type": 0,
            "groups": [],
            "name": "",
            "vote_locked": false,
            "description": "",
            "args": [],
            "examples": [],
            "premium_only": false,
            "notes": [],
            "doc_link": "",
            "id": null,
            "nsfw": false
        }
    ]
}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [Bot](https://docs.fateslist.xyz/endpoints#authorization)


### Delete Bot Command
#### DELETE /bots/{id}/commands


DELETE a command.

The ``id`` here must be the bot id you wish to add the command for

``names`` and ``ids`` must be a ``|`` seperated list of ``names`` or valid
UUIDs in the case of ids. Bad names/ids will be ignored


**API v2 analogue:** None

**Path parameters**

- **id** [i64 (type info may be incomplete, see example)]


**Example**

```json
{
    "id": 0
}
```

**Query parameters**

- **nuke** [Optional <bool> (type info may be incomplete, see example)]
- **names** [String? | default = command name|command name 2 (type info may be incomplete, see example)]
- **ids** [String? | default = id 1|id 2 (type info may be incomplete, see example)]


**Example**

```json
{
    "nuke": false,
    "names": "command name|command name 2",
    "ids": "id 1|id 2"
}
```

**Request Body**

```json
{}
```

**Response Body**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [Bot](https://docs.fateslist.xyz/endpoints#authorization)


