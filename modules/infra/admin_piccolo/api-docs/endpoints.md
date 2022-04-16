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


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**




**Request Body Description**

- **guild_count** => i64 [default/example = 3939]
- **shard_count** => (Optional) i64 [default/example = 48484]
- **shards** => (Optional) (Array) i32 [default/example = 149]i32 [default/example = 22020]
- **user_count** => (Optional) i64 [default/example = 39393]



**Request Body Example**

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

**Response Body Description**

- **done** => bool [default/example = false]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": false,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [Bot](https://lynx.fateslist.xyz/docs/endpoints#authorization)


### Index
#### GET /index

Returns the index for bots and servers

**Path parameters**




**Query parameters**

- **target_type** => (Optional) string [default/example = "bot"]



**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **new** => (Array) Struct IndexBot 
	- **guild_count** => i64 [default/example = 0]
	- **description** => string [default/example = ""]
	- **banner** => string [default/example = ""]
	- **nsfw** => bool [default/example = false]
	- **votes** => i64 [default/example = 0]
	- **state** => i32 [default/example = 0]
	- **user** => Struct User 
		- **id** => string [default/example = ""]
		- **username** => string [default/example = ""]
		- **disc** => string [default/example = ""]
		- **avatar** => string [default/example = ""]
		- **bot** => bool [default/example = false]
		- **status** => string [default/example = "Unknown"]



	- **flags** => (Array) 



- **top_voted** => (Array) Struct IndexBot 
	- **guild_count** => i64 [default/example = 0]
	- **description** => string [default/example = ""]
	- **banner** => string [default/example = ""]
	- **nsfw** => bool [default/example = false]
	- **votes** => i64 [default/example = 0]
	- **state** => i32 [default/example = 0]
	- **user** => Struct User 
		- **id** => string [default/example = ""]
		- **username** => string [default/example = ""]
		- **disc** => string [default/example = ""]
		- **avatar** => string [default/example = ""]
		- **bot** => bool [default/example = false]
		- **status** => string [default/example = "Unknown"]



	- **flags** => (Array) 



- **certified** => (Array) Struct IndexBot 
	- **guild_count** => i64 [default/example = 0]
	- **description** => string [default/example = ""]
	- **banner** => string [default/example = ""]
	- **nsfw** => bool [default/example = false]
	- **votes** => i64 [default/example = 0]
	- **state** => i32 [default/example = 0]
	- **user** => Struct User 
		- **id** => string [default/example = ""]
		- **username** => string [default/example = ""]
		- **disc** => string [default/example = ""]
		- **avatar** => string [default/example = ""]
		- **bot** => bool [default/example = false]
		- **status** => string [default/example = "Unknown"]



	- **flags** => (Array) 



- **tags** => (Array) Struct Tag 
	- **name** => string [default/example = ""]
	- **iconify_data** => string [default/example = ""]
	- **id** => string [default/example = ""]
	- **owner_guild** => None (unknown value type)



- **features** => (Array) Struct Feature 
	- **id** => string [default/example = ""]
	- **name** => string [default/example = ""]
	- **viewed_as** => string [default/example = ""]
	- **description** => string [default/example = ""]






**Response Body Example**

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


### Docs Template
#### GET /_docs_template

Internal route to return docs template

**Path parameters**




**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**




**Response Body Example**

```json
{}
```
**Authorization Needed** | 


### Enum Docs Template
#### GET /_enum_docs_template

Internal route to return enum docs template

**Path parameters**




**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**




**Response Body Example**

```json
{}
```
**Authorization Needed** | 


### Resolve Vanity
#### GET /code/{code}

Resolves the vanity for a bot/server in the list

**Path parameters**

- **code** => string [default/example = "my-vanity"]



**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **target_type** => string [default/example = "bot | server"]
- **target_id** => string [default/example = "0000000000"]



**Response Body Example**

```json
{
    "target_type": "bot | server",
    "target_id": "0000000000"
}
```
**Authorization Needed** | 


### Get Partners
#### GET /partners

Get policies (rules, privacy policy, terms of service)

**Path parameters**




**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **partners** => (Array) Struct Partner 
	- **id** => string [default/example = "0"]
	- **name** => string [default/example = "My development"]
	- **owner** => string [default/example = "12345678901234567"]
	- **image** => string [default/example = ""]
	- **description** => string [default/example = "Some random description"]
	- **links** => 	- **discord** => string [default/example = "https://discord.com/lmao"]
	- **website** => string [default/example = "https://example.com"]





- **icons** => 




**Response Body Example**

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

**Path parameters**




**Query parameters**




**Request Body Description**

- **text** => string [default/example = ""]
- **long_description_type** => i32 [default/example = 1]



**Request Body Example**

```json
{
    "text": "",
    "long_description_type": 1
}
```

**Response Body Description**

- **preview** => string [default/example = ""]



**Response Body Example**

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

This API returns some empty fields such as ``webhook``, ``webhook_secret``, ``api_token`` and more. 
This is to allow reuse of the Bot struct in Get Bot Settings which *does* contain this sensitive data. 

**Set the Frostpaw header if you are a custom client. Send Frostpaw-Invite header on invites**


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **user** => Struct User 
	- **id** => string [default/example = ""]
	- **username** => string [default/example = ""]
	- **disc** => string [default/example = ""]
	- **avatar** => string [default/example = ""]
	- **bot** => bool [default/example = false]
	- **status** => string [default/example = "Unknown"]



- **description** => string [default/example = ""]
- **tags** => (Array) 
- **created_at** => string [default/example = "1970-01-01T00:00:00Z"]
- **last_updated_at** => string [default/example = "1970-01-01T00:00:00Z"]
- **last_stats_post** => string [default/example = "1970-01-01T00:00:00Z"]
- **long_description** => string [default/example = "blah blah blah"]
- **long_description_raw** => string [default/example = "blah blah blah unsanitized"]
- **long_description_type** => i32 [default/example = 1]
- **guild_count** => i64 [default/example = 0]
- **shard_count** => i64 [default/example = 493]
- **user_count** => i64 [default/example = 0]
- **shards** => (Array) 
- **prefix** => (Optional) string [default/example = "Some prefix, null = slash command"]
- **library** => string [default/example = ""]
- **invite** => (Optional) string [default/example = "Raw invite, null = auto-generated. Use invite_link instead"]
- **invite_link** => string [default/example = "https://discord.com/api/oauth2/authorize...."]
- **invite_amount** => i32 [default/example = 48]
- **owners** => (Array) Struct BotOwner 
	- **user** => Struct User 
		- **id** => string [default/example = ""]
		- **username** => string [default/example = ""]
		- **disc** => string [default/example = ""]
		- **avatar** => string [default/example = ""]
		- **bot** => bool [default/example = false]
		- **status** => string [default/example = "Unknown"]



	- **main** => bool [default/example = false]



- **owners_html** => string [default/example = ""]
- **features** => (Array) Struct Feature 
	- **id** => string [default/example = ""]
	- **name** => string [default/example = ""]
	- **viewed_as** => string [default/example = ""]
	- **description** => string [default/example = ""]



- **state** => i32 [default/example = 0]
- **page_style** => i32 [default/example = 1]
- **website** => (Optional) string [default/example = "https://example.com"]
- **support** => (Optional) string [default/example = ""]
- **github** => (Optional) string [default/example = "https://github.com/Fates-List/FatesList"]
- **css** => string [default/example = "<style></style>"]
- **votes** => i64 [default/example = 0]
- **total_votes** => i64 [default/example = 0]
- **vanity** => string [default/example = ""]
- **donate** => (Optional) string [default/example = "https://paypal.me/example"]
- **privacy_policy** => (Optional) string [default/example = "https://lynx.fateslist.xyz/frostpaw/tos"]
- **nsfw** => bool [default/example = false]
- **banner_card** => (Optional) string [default/example = "https://api.fateslist.xyz/static/botlisticon.webp"]
- **banner_page** => (Optional) string [default/example = "https://api.fateslist.xyz/static/botlisticon.webp"]
- **keep_banner_decor** => bool [default/example = false]
- **client_id** => string [default/example = ""]
- **flags** => (Array) 
- **action_logs** => (Array) Struct ActionLog 
	- **user_id** => string [default/example = ""]
	- **bot_id** => string [default/example = ""]
	- **action** => i32 [default/example = 0]
	- **action_time** => string [default/example = "1970-01-01T00:00:00Z"]
	- **context** => (Optional) string [default/example = "Some context as to why the action happened"]



- **vpm** => (Optional) (Array) Struct VotesPerMonth 
	- **votes** => i64 [default/example = 0]
	- **ts** => string [default/example = "1970-01-01T00:00:00Z"]



- **uptime_checks_total** => (Optional) i32 [default/example = 30]
- **uptime_checks_failed** => (Optional) i32 [default/example = 19]
- **commands** => - **default** => (Array) Struct BotCommand 
	- **cmd_type** => i32 [default/example = 0]
	- **groups** => (Array) 
	- **name** => string [default/example = ""]
	- **vote_locked** => bool [default/example = false]
	- **description** => string [default/example = ""]
	- **args** => (Array) 
	- **examples** => (Array) 
	- **premium_only** => bool [default/example = false]
	- **notes** => (Array) 
	- **doc_link** => None (unknown value type)
	- **id** => None (unknown value type)
	- **nsfw** => bool [default/example = false]





- **resources** => (Array) Struct Resource 
	- **id** => None (unknown value type)
	- **resource_title** => string [default/example = ""]
	- **resource_link** => string [default/example = ""]
	- **resource_description** => string [default/example = ""]



- **webhook** => (Optional) string [default/example = "This will be redacted for Get Bot endpoint"]
- **webhook_secret** => (Optional) string [default/example = "This (along with ``webhook_type``, ``api_token`` and ``webhook_hmac_only``) will be redacted for Get Bot endpoint"]
- **webhook_type** => None (unknown value type)
- **webhook_hmac_only** => None (unknown value type)
- **api_token** => (Optional) string [default/example = "This will be redacted for Get Bot endpoint"]



**Response Body Example**

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
    "prefix": "Some prefix, null = slash command",
    "library": "",
    "invite": "Raw invite, null = auto-generated. Use invite_link instead",
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
    "website": "https://example.com",
    "support": "",
    "github": "https://github.com/Fates-List/FatesList",
    "css": "<style></style>",
    "votes": 0,
    "total_votes": 0,
    "vanity": "",
    "donate": "https://paypal.me/example",
    "privacy_policy": "https://lynx.fateslist.xyz/frostpaw/tos",
    "nsfw": false,
    "banner_card": "https://api.fateslist.xyz/static/botlisticon.webp",
    "banner_page": "https://api.fateslist.xyz/static/botlisticon.webp",
    "keep_banner_decor": false,
    "client_id": "",
    "flags": [],
    "action_logs": [
        {
            "user_id": "",
            "bot_id": "",
            "action": 0,
            "action_time": "1970-01-01T00:00:00Z",
            "context": "Some context as to why the action happened"
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
                "doc_link": null,
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
    "webhook_secret": "This (along with ``webhook_type``, ``api_token`` and ``webhook_hmac_only``) will be redacted for Get Bot endpoint",
    "webhook_type": null,
    "webhook_hmac_only": null,
    "api_token": "This will be redacted for Get Bot endpoint"
}
```
**Authorization Needed** | 


### Search List
#### GET /search?q={query}


Searches the list based on a query named ``q``. 
        
Using -1 for ``gc_to`` will disable ``gc_to`` field

**Path parameters**




**Query parameters**

- **q** => string [default/example = "mew"]
- **gc_from** => i64 [default/example = 1]
- **gc_to** => i64 [default/example = -1]



**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **bots** => (Array) Struct IndexBot 
	- **guild_count** => i64 [default/example = 0]
	- **description** => string [default/example = ""]
	- **banner** => string [default/example = ""]
	- **nsfw** => bool [default/example = false]
	- **votes** => i64 [default/example = 0]
	- **state** => i32 [default/example = 0]
	- **user** => Struct User 
		- **id** => string [default/example = ""]
		- **username** => string [default/example = ""]
		- **disc** => string [default/example = ""]
		- **avatar** => string [default/example = ""]
		- **bot** => bool [default/example = false]
		- **status** => string [default/example = "Unknown"]



	- **flags** => (Array) 



- **servers** => (Array) Struct IndexBot 
	- **guild_count** => i64 [default/example = 0]
	- **description** => string [default/example = ""]
	- **banner** => string [default/example = ""]
	- **nsfw** => bool [default/example = false]
	- **votes** => i64 [default/example = 0]
	- **state** => i32 [default/example = 0]
	- **user** => Struct User 
		- **id** => string [default/example = ""]
		- **username** => string [default/example = ""]
		- **disc** => string [default/example = ""]
		- **avatar** => string [default/example = ""]
		- **bot** => bool [default/example = false]
		- **status** => string [default/example = "Unknown"]



	- **flags** => (Array) 



- **profiles** => (Array) Struct SearchProfile 
	- **banner** => string [default/example = ""]
	- **description** => string [default/example = ""]
	- **user** => Struct User 
		- **id** => string [default/example = ""]
		- **username** => string [default/example = ""]
		- **disc** => string [default/example = ""]
		- **avatar** => string [default/example = ""]
		- **bot** => bool [default/example = false]
		- **status** => string [default/example = "Unknown"]






- **packs** => (Array) Struct BotPack 
	- **id** => string [default/example = "0"]
	- **name** => string [default/example = ""]
	- **description** => string [default/example = ""]
	- **icon** => string [default/example = ""]
	- **banner** => string [default/example = ""]
	- **resolved_bots** => (Array) Struct ResolvedPackBot 
		- **user** => Struct User 
			- **id** => string [default/example = ""]
			- **username** => string [default/example = ""]
			- **disc** => string [default/example = ""]
			- **avatar** => string [default/example = ""]
			- **bot** => bool [default/example = false]
			- **status** => string [default/example = "Unknown"]



		- **description** => string [default/example = ""]



	- **owner** => Struct User 
		- **id** => string [default/example = ""]
		- **username** => string [default/example = ""]
		- **disc** => string [default/example = ""]
		- **avatar** => string [default/example = ""]
		- **bot** => bool [default/example = false]
		- **status** => string [default/example = "Unknown"]



	- **created_at** => string [default/example = "1970-01-01T00:00:00Z"]



- **tags** => Struct SearchTags 
	- **bots** => (Array) Struct Tag 
		- **name** => string [default/example = ""]
		- **iconify_data** => string [default/example = ""]
		- **id** => string [default/example = ""]
		- **owner_guild** => None (unknown value type)



	- **servers** => (Array) Struct Tag 
		- **name** => string [default/example = ""]
		- **iconify_data** => string [default/example = ""]
		- **id** => string [default/example = ""]
		- **owner_guild** => None (unknown value type)









**Response Body Example**

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

**Path parameters**




**Query parameters**

- **q** => string [default/example = "music"]



**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **bots** => (Array) Struct IndexBot 
	- **guild_count** => i64 [default/example = 0]
	- **description** => string [default/example = ""]
	- **banner** => string [default/example = ""]
	- **nsfw** => bool [default/example = false]
	- **votes** => i64 [default/example = 0]
	- **state** => i32 [default/example = 0]
	- **user** => Struct User 
		- **id** => string [default/example = ""]
		- **username** => string [default/example = ""]
		- **disc** => string [default/example = ""]
		- **avatar** => string [default/example = ""]
		- **bot** => bool [default/example = false]
		- **status** => string [default/example = "Unknown"]



	- **flags** => (Array) 



- **servers** => (Array) Struct IndexBot 
	- **guild_count** => i64 [default/example = 0]
	- **description** => string [default/example = ""]
	- **banner** => string [default/example = ""]
	- **nsfw** => bool [default/example = false]
	- **votes** => i64 [default/example = 0]
	- **state** => i32 [default/example = 0]
	- **user** => Struct User 
		- **id** => string [default/example = ""]
		- **username** => string [default/example = ""]
		- **disc** => string [default/example = ""]
		- **avatar** => string [default/example = ""]
		- **bot** => bool [default/example = false]
		- **status** => string [default/example = "Unknown"]



	- **flags** => (Array) 



- **profiles** => (Array) 
- **packs** => (Array) 
- **tags** => Struct SearchTags 
	- **bots** => (Array) Struct Tag 
		- **name** => string [default/example = ""]
		- **iconify_data** => string [default/example = ""]
		- **id** => string [default/example = ""]
		- **owner_guild** => None (unknown value type)



	- **servers** => (Array) Struct Tag 
		- **name** => string [default/example = ""]
		- **iconify_data** => string [default/example = ""]
		- **id** => string [default/example = ""]
		- **owner_guild** => None (unknown value type)









**Response Body Example**

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


**Path parameters**




**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **guild_count** => i64 [default/example = 0]
- **description** => string [default/example = ""]
- **banner** => string [default/example = ""]
- **nsfw** => bool [default/example = false]
- **votes** => i64 [default/example = 0]
- **state** => i32 [default/example = 0]
- **user** => Struct User 
	- **id** => string [default/example = ""]
	- **username** => string [default/example = ""]
	- **disc** => string [default/example = ""]
	- **avatar** => string [default/example = ""]
	- **bot** => bool [default/example = false]
	- **status** => string [default/example = "Unknown"]



- **flags** => (Array) 



**Response Body Example**

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


**Path parameters**




**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **guild_count** => i64 [default/example = 0]
- **description** => string [default/example = ""]
- **banner** => string [default/example = ""]
- **nsfw** => bool [default/example = false]
- **votes** => i64 [default/example = 0]
- **state** => i32 [default/example = 0]
- **user** => Struct User 
	- **id** => string [default/example = ""]
	- **username** => string [default/example = ""]
	- **disc** => string [default/example = ""]
	- **avatar** => string [default/example = ""]
	- **bot** => bool [default/example = false]
	- **status** => string [default/example = "Unknown"]



- **flags** => (Array) 



**Response Body Example**

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


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **user** => Struct User 
	- **id** => string [default/example = ""]
	- **username** => string [default/example = ""]
	- **disc** => string [default/example = ""]
	- **avatar** => string [default/example = ""]
	- **bot** => bool [default/example = false]
	- **status** => string [default/example = "Unknown"]



- **description** => string [default/example = ""]
- **tags** => (Array) 
- **long_description_type** => i32 [default/example = 1]
- **long_description** => string [default/example = ""]
- **long_description_raw** => string [default/example = ""]
- **vanity** => (Optional) string [default/example = "server-vanity"]
- **guild_count** => i64 [default/example = 0]
- **invite_amount** => i32 [default/example = 0]
- **invite_link** => (Optional) string [default/example = "Only present if ``Frostpaw-Invite`` header is set"]
- **created_at** => string [default/example = "1970-01-01T00:00:00Z"]
- **state** => i32 [default/example = 0]
- **flags** => (Array) 
- **css** => string [default/example = ""]
- **website** => (Optional) string [default/example = "https://frostpaw.com"]
- **banner_card** => (Optional) string [default/example = "https://frostpaw.com/assets/img/banner-card.png"]
- **banner_page** => (Optional) string [default/example = "https://frostpaw.com/assets/img/banner-page.png"]
- **keep_banner_decor** => bool [default/example = false]
- **nsfw** => bool [default/example = false]
- **votes** => i64 [default/example = 0]
- **total_votes** => i64 [default/example = 0]



**Response Body Example**

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
    "vanity": "server-vanity",
    "guild_count": 0,
    "invite_amount": 0,
    "invite_link": "Only present if ``Frostpaw-Invite`` header is set",
    "created_at": "1970-01-01T00:00:00Z",
    "state": 0,
    "flags": [],
    "css": "",
    "website": "https://frostpaw.com",
    "banner_card": "https://frostpaw.com/assets/img/banner-card.png",
    "banner_page": "https://frostpaw.com/assets/img/banner-page.png",
    "keep_banner_decor": false,
    "nsfw": false,
    "votes": 0,
    "total_votes": 0
}
```
**Authorization Needed** | 


### Get Bot Votes
#### GET /users/{user_id}/bots/{bot_id}/votes


Endpoint to check amount of votes a user has.

- votes | The amount of votes the bot has.
- voted | Whether or not the user has *ever* voted for the bot.
- timestamps | A list of timestamps that the user has voted for the bot on that has been recorded.
- expiry | The time when the user can next vote.
- vote_right_now | Whether a user can vote right now. Currently equivalent to `vote_epoch < 0`.

Differences from API v2:

- Unlike API v2, this does not require authorization to use. This is to speed up responses and 
because the last thing people want to scrape are Fates List user votes anyways. **You should not rely on
this however, it is prone to change *anytime* in the future**.
- ``vts`` has been renamed to ``timestamps``


**Path parameters**

- **user_id** => i64 [default/example = 0]
- **bot_id** => i64 [default/example = 0]



**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **votes** => i64 [default/example = 10]
- **voted** => bool [default/example = true]
- **vote_right_now** => bool [default/example = false]
- **expiry** => u64 [default/example = 101]
- **timestamps** => (Array) string [default/example = "1970-01-01T00:00:00Z"]



**Response Body Example**

```json
{
    "votes": 10,
    "voted": true,
    "vote_right_now": false,
    "expiry": 101,
    "timestamps": [
        "1970-01-01T00:00:00Z"
    ]
}
```
**Authorization Needed** | 


### Create Bot Vote
#### PATCH /users/{user_id}/bots/{bot_id}/votes


This endpoint creates a vote for a bot which can only be done *once* every 8 hours.


**Path parameters**

- **user_id** => i64 [default/example = 0]
- **bot_id** => i64 [default/example = 0]



**Query parameters**

- **test** => bool [default/example = true]



**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **done** => bool [default/example = false]
- **reason** => (Optional) string [default/example = "Why the vote failed or any extra info to send to client if the vote succeeded"]
- **context** => (Optional) string [default/example = "Some context on the vote"]



**Response Body Example**

```json
{
    "done": false,
    "reason": "Why the vote failed or any extra info to send to client if the vote succeeded",
    "context": "Some context on the vote"
}
```
**Authorization Needed** | [User](https://lynx.fateslist.xyz/docs/endpoints#authorization)


### Create Server Vote
#### PATCH /users/{user_id}/servers/{server_id}/votes


This endpoint creates a vote for a server which can only be done *once* every 8 hours
and is independent from a bot vote.


**Path parameters**

- **user_id** => i64 [default/example = 0]
- **server_id** => i64 [default/example = 0]



**Query parameters**

- **test** => bool [default/example = true]



**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **done** => bool [default/example = false]
- **reason** => (Optional) string [default/example = "Why the vote failed or any extra info to send to client if the vote succeeded"]
- **context** => (Optional) string [default/example = "Some context on the vote"]



**Response Body Example**

```json
{
    "done": false,
    "reason": "Why the vote failed or any extra info to send to client if the vote succeeded",
    "context": "Some context on the vote"
}
```
**Authorization Needed** | [User](https://lynx.fateslist.xyz/docs/endpoints#authorization)


### Mini Index
#### GET /mini-index


Returns a mini-index which is basically a Index but with only ``tags``
and ``features`` having any data. Other fields are empty arrays/vectors.

This is used internally by sunbeam for the add bot system where a full bot
index is too costly and making a new struct is unnecessary.


**Path parameters**




**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **new** => (Array) 
- **top_voted** => (Array) 
- **certified** => (Array) 
- **tags** => (Array) Struct Tag 
	- **name** => string [default/example = ""]
	- **iconify_data** => string [default/example = ""]
	- **id** => string [default/example = ""]
	- **owner_guild** => None (unknown value type)



- **features** => (Array) Struct Feature 
	- **id** => string [default/example = ""]
	- **name** => string [default/example = ""]
	- **viewed_as** => string [default/example = ""]
	- **description** => string [default/example = ""]






**Response Body Example**

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


**Path parameters**

- **user_id** => i64 [default/example = 0]
- **bot_id** => i64 [default/example = 0]



**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **bot** => Struct Bot 
	- **user** => Struct User 
		- **id** => string [default/example = ""]
		- **username** => string [default/example = ""]
		- **disc** => string [default/example = ""]
		- **avatar** => string [default/example = ""]
		- **bot** => bool [default/example = false]
		- **status** => string [default/example = "Unknown"]



	- **description** => string [default/example = ""]
	- **tags** => (Array) 
	- **created_at** => string [default/example = "1970-01-01T00:00:00Z"]
	- **last_updated_at** => string [default/example = "1970-01-01T00:00:00Z"]
	- **last_stats_post** => string [default/example = "1970-01-01T00:00:00Z"]
	- **long_description** => string [default/example = "blah blah blah"]
	- **long_description_raw** => string [default/example = "blah blah blah unsanitized"]
	- **long_description_type** => i32 [default/example = 1]
	- **guild_count** => i64 [default/example = 0]
	- **shard_count** => i64 [default/example = 493]
	- **user_count** => i64 [default/example = 0]
	- **shards** => (Array) 
	- **prefix** => (Optional) string [default/example = "Some prefix, null = slash command"]
	- **library** => string [default/example = ""]
	- **invite** => (Optional) string [default/example = "Raw invite, null = auto-generated. Use invite_link instead"]
	- **invite_link** => string [default/example = "https://discord.com/api/oauth2/authorize...."]
	- **invite_amount** => i32 [default/example = 48]
	- **owners** => (Array) Struct BotOwner 
		- **user** => Struct User 
			- **id** => string [default/example = ""]
			- **username** => string [default/example = ""]
			- **disc** => string [default/example = ""]
			- **avatar** => string [default/example = ""]
			- **bot** => bool [default/example = false]
			- **status** => string [default/example = "Unknown"]



		- **main** => bool [default/example = false]



	- **owners_html** => string [default/example = ""]
	- **features** => (Array) Struct Feature 
		- **id** => string [default/example = ""]
		- **name** => string [default/example = ""]
		- **viewed_as** => string [default/example = ""]
		- **description** => string [default/example = ""]



	- **state** => i32 [default/example = 0]
	- **page_style** => i32 [default/example = 1]
	- **website** => (Optional) string [default/example = "https://example.com"]
	- **support** => (Optional) string [default/example = ""]
	- **github** => (Optional) string [default/example = "https://github.com/Fates-List/FatesList"]
	- **css** => string [default/example = "<style></style>"]
	- **votes** => i64 [default/example = 0]
	- **total_votes** => i64 [default/example = 0]
	- **vanity** => string [default/example = ""]
	- **donate** => (Optional) string [default/example = "https://paypal.me/example"]
	- **privacy_policy** => (Optional) string [default/example = "https://lynx.fateslist.xyz/frostpaw/tos"]
	- **nsfw** => bool [default/example = false]
	- **banner_card** => (Optional) string [default/example = "https://api.fateslist.xyz/static/botlisticon.webp"]
	- **banner_page** => (Optional) string [default/example = "https://api.fateslist.xyz/static/botlisticon.webp"]
	- **keep_banner_decor** => bool [default/example = false]
	- **client_id** => string [default/example = ""]
	- **flags** => (Array) 
	- **action_logs** => (Array) Struct ActionLog 
		- **user_id** => string [default/example = ""]
		- **bot_id** => string [default/example = ""]
		- **action** => i32 [default/example = 0]
		- **action_time** => string [default/example = "1970-01-01T00:00:00Z"]
		- **context** => (Optional) string [default/example = "Some context as to why the action happened"]



	- **vpm** => (Optional) (Array) Struct VotesPerMonth 
		- **votes** => i64 [default/example = 0]
		- **ts** => string [default/example = "1970-01-01T00:00:00Z"]



	- **uptime_checks_total** => (Optional) i32 [default/example = 30]
	- **uptime_checks_failed** => (Optional) i32 [default/example = 19]
	- **commands** => 	- **default** => (Array) Struct BotCommand 
		- **cmd_type** => i32 [default/example = 0]
		- **groups** => (Array) 
		- **name** => string [default/example = ""]
		- **vote_locked** => bool [default/example = false]
		- **description** => string [default/example = ""]
		- **args** => (Array) 
		- **examples** => (Array) 
		- **premium_only** => bool [default/example = false]
		- **notes** => (Array) 
		- **doc_link** => None (unknown value type)
		- **id** => None (unknown value type)
		- **nsfw** => bool [default/example = false]






- **resources** => (Array) Struct Resource 
	- **id** => None (unknown value type)
	- **resource_title** => string [default/example = ""]
	- **resource_link** => string [default/example = ""]
	- **resource_description** => string [default/example = ""]



- **webhook** => (Optional) string [default/example = "This will be redacted for Get Bot endpoint"]
- **webhook_secret** => (Optional) string [default/example = "This (along with ``webhook_type``, ``api_token`` and ``webhook_hmac_only``) will be redacted for Get Bot endpoint"]
- **webhook_type** => None (unknown value type)
- **webhook_hmac_only** => None (unknown value type)
- **api_token** => (Optional) string [default/example = "This will be redacted for Get Bot endpoint"]


- **context** => Struct BotSettingsContext 
	- **tags** => (Array) Struct Tag 
		- **name** => string [default/example = ""]
		- **iconify_data** => string [default/example = ""]
		- **id** => string [default/example = ""]
		- **owner_guild** => None (unknown value type)



	- **features** => (Array) Struct Feature 
		- **id** => string [default/example = ""]
		- **name** => string [default/example = ""]
		- **viewed_as** => string [default/example = ""]
		- **description** => string [default/example = ""]









**Response Body Example**

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
        "prefix": "Some prefix, null = slash command",
        "library": "",
        "invite": "Raw invite, null = auto-generated. Use invite_link instead",
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
        "website": "https://example.com",
        "support": "",
        "github": "https://github.com/Fates-List/FatesList",
        "css": "<style></style>",
        "votes": 0,
        "total_votes": 0,
        "vanity": "",
        "donate": "https://paypal.me/example",
        "privacy_policy": "https://lynx.fateslist.xyz/frostpaw/tos",
        "nsfw": false,
        "banner_card": "https://api.fateslist.xyz/static/botlisticon.webp",
        "banner_page": "https://api.fateslist.xyz/static/botlisticon.webp",
        "keep_banner_decor": false,
        "client_id": "",
        "flags": [],
        "action_logs": [
            {
                "user_id": "",
                "bot_id": "",
                "action": 0,
                "action_time": "1970-01-01T00:00:00Z",
                "context": "Some context as to why the action happened"
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
                    "doc_link": null,
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
        "webhook_secret": "This (along with ``webhook_type``, ``api_token`` and ``webhook_hmac_only``) will be redacted for Get Bot endpoint",
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
**Authorization Needed** | [User](https://lynx.fateslist.xyz/docs/endpoints#authorization)


## Auth

### Get OAuth2 Link
#### GET /oauth2

Returns the oauth2 link used to login with. ``reason`` contains the state UUID

**Path parameters**




**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => (Optional) string [default/example = "https://discord.com/........."]



**Response Body Example**

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

**Path parameters**




**Query parameters**




**Request Body Description**

- **code** => string [default/example = "code from discord oauth"]
- **state** => (Optional) string [default/example = "Random UUID right now"]



**Request Body Example**

```json
{
    "code": "code from discord oauth",
    "state": "Random UUID right now"
}
```

**Response Body Description**

- **state** => i32 [default/example = 0]
- **token** => string [default/example = ""]
- **user** => Struct User 
	- **id** => string [default/example = ""]
	- **username** => string [default/example = ""]
	- **disc** => string [default/example = ""]
	- **avatar** => string [default/example = ""]
	- **bot** => bool [default/example = false]
	- **status** => string [default/example = "Unknown"]



- **site_lang** => string [default/example = ""]
- **css** => None (unknown value type)



**Response Body Example**

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


**Path parameters**




**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

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


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [Bot](https://lynx.fateslist.xyz/docs/endpoints#authorization)


### New User Token
#### DELETE /users/{id}/token


'Deletes' a user token and reissues a new user token. Use this if your user
token ever gets leaked.


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://lynx.fateslist.xyz/docs/endpoints#authorization)


### New Server Token
#### DELETE /servers/{id}/token


'Deletes' a server token and reissues a new server token. Use this if your server
token ever gets leaked.


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [Server](https://lynx.fateslist.xyz/docs/endpoints#authorization)


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


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**




**Request Body Description**

- **user** => Struct User 
	- **id** => string [default/example = ""]
	- **username** => string [default/example = ""]
	- **disc** => string [default/example = ""]
	- **avatar** => string [default/example = ""]
	- **bot** => bool [default/example = false]
	- **status** => string [default/example = "Unknown"]



- **description** => string [default/example = ""]
- **tags** => (Array) 
- **created_at** => string [default/example = "1970-01-01T00:00:00Z"]
- **last_updated_at** => string [default/example = "1970-01-01T00:00:00Z"]
- **last_stats_post** => string [default/example = "1970-01-01T00:00:00Z"]
- **long_description** => string [default/example = "blah blah blah"]
- **long_description_raw** => string [default/example = "blah blah blah unsanitized"]
- **long_description_type** => i32 [default/example = 1]
- **guild_count** => i64 [default/example = 0]
- **shard_count** => i64 [default/example = 493]
- **user_count** => i64 [default/example = 0]
- **shards** => (Array) 
- **prefix** => (Optional) string [default/example = "Some prefix, null = slash command"]
- **library** => string [default/example = ""]
- **invite** => (Optional) string [default/example = "Raw invite, null = auto-generated. Use invite_link instead"]
- **invite_link** => string [default/example = "https://discord.com/api/oauth2/authorize...."]
- **invite_amount** => i32 [default/example = 48]
- **owners** => (Array) Struct BotOwner 
	- **user** => Struct User 
		- **id** => string [default/example = ""]
		- **username** => string [default/example = ""]
		- **disc** => string [default/example = ""]
		- **avatar** => string [default/example = ""]
		- **bot** => bool [default/example = false]
		- **status** => string [default/example = "Unknown"]



	- **main** => bool [default/example = false]



- **owners_html** => string [default/example = ""]
- **features** => (Array) Struct Feature 
	- **id** => string [default/example = ""]
	- **name** => string [default/example = ""]
	- **viewed_as** => string [default/example = ""]
	- **description** => string [default/example = ""]



- **state** => i32 [default/example = 0]
- **page_style** => i32 [default/example = 1]
- **website** => (Optional) string [default/example = "https://example.com"]
- **support** => (Optional) string [default/example = ""]
- **github** => (Optional) string [default/example = "https://github.com/Fates-List/FatesList"]
- **css** => string [default/example = "<style></style>"]
- **votes** => i64 [default/example = 0]
- **total_votes** => i64 [default/example = 0]
- **vanity** => string [default/example = ""]
- **donate** => (Optional) string [default/example = "https://paypal.me/example"]
- **privacy_policy** => (Optional) string [default/example = "https://lynx.fateslist.xyz/frostpaw/tos"]
- **nsfw** => bool [default/example = false]
- **banner_card** => (Optional) string [default/example = "https://api.fateslist.xyz/static/botlisticon.webp"]
- **banner_page** => (Optional) string [default/example = "https://api.fateslist.xyz/static/botlisticon.webp"]
- **keep_banner_decor** => bool [default/example = false]
- **client_id** => string [default/example = ""]
- **flags** => (Array) 
- **action_logs** => (Array) Struct ActionLog 
	- **user_id** => string [default/example = ""]
	- **bot_id** => string [default/example = ""]
	- **action** => i32 [default/example = 0]
	- **action_time** => string [default/example = "1970-01-01T00:00:00Z"]
	- **context** => (Optional) string [default/example = "Some context as to why the action happened"]



- **vpm** => (Optional) (Array) Struct VotesPerMonth 
	- **votes** => i64 [default/example = 0]
	- **ts** => string [default/example = "1970-01-01T00:00:00Z"]



- **uptime_checks_total** => (Optional) i32 [default/example = 30]
- **uptime_checks_failed** => (Optional) i32 [default/example = 19]
- **commands** => - **default** => (Array) Struct BotCommand 
	- **cmd_type** => i32 [default/example = 0]
	- **groups** => (Array) 
	- **name** => string [default/example = ""]
	- **vote_locked** => bool [default/example = false]
	- **description** => string [default/example = ""]
	- **args** => (Array) 
	- **examples** => (Array) 
	- **premium_only** => bool [default/example = false]
	- **notes** => (Array) 
	- **doc_link** => None (unknown value type)
	- **id** => None (unknown value type)
	- **nsfw** => bool [default/example = false]





- **resources** => (Array) Struct Resource 
	- **id** => None (unknown value type)
	- **resource_title** => string [default/example = ""]
	- **resource_link** => string [default/example = ""]
	- **resource_description** => string [default/example = ""]



- **webhook** => (Optional) string [default/example = "This will be redacted for Get Bot endpoint"]
- **webhook_secret** => (Optional) string [default/example = "This (along with ``webhook_type``, ``api_token`` and ``webhook_hmac_only``) will be redacted for Get Bot endpoint"]
- **webhook_type** => None (unknown value type)
- **webhook_hmac_only** => None (unknown value type)
- **api_token** => (Optional) string [default/example = "This will be redacted for Get Bot endpoint"]



**Request Body Example**

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
    "prefix": "Some prefix, null = slash command",
    "library": "",
    "invite": "Raw invite, null = auto-generated. Use invite_link instead",
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
    "website": "https://example.com",
    "support": "",
    "github": "https://github.com/Fates-List/FatesList",
    "css": "<style></style>",
    "votes": 0,
    "total_votes": 0,
    "vanity": "",
    "donate": "https://paypal.me/example",
    "privacy_policy": "https://lynx.fateslist.xyz/frostpaw/tos",
    "nsfw": false,
    "banner_card": "https://api.fateslist.xyz/static/botlisticon.webp",
    "banner_page": "https://api.fateslist.xyz/static/botlisticon.webp",
    "keep_banner_decor": false,
    "client_id": "",
    "flags": [],
    "action_logs": [
        {
            "user_id": "",
            "bot_id": "",
            "action": 0,
            "action_time": "1970-01-01T00:00:00Z",
            "context": "Some context as to why the action happened"
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
                "doc_link": null,
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
    "webhook_secret": "This (along with ``webhook_type``, ``api_token`` and ``webhook_hmac_only``) will be redacted for Get Bot endpoint",
    "webhook_type": null,
    "webhook_hmac_only": null,
    "api_token": "This will be redacted for Get Bot endpoint"
}
```

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://lynx.fateslist.xyz/docs/endpoints#authorization)


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


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**




**Request Body Description**

- **user** => Struct User 
	- **id** => string [default/example = ""]
	- **username** => string [default/example = ""]
	- **disc** => string [default/example = ""]
	- **avatar** => string [default/example = ""]
	- **bot** => bool [default/example = false]
	- **status** => string [default/example = "Unknown"]



- **description** => string [default/example = ""]
- **tags** => (Array) 
- **created_at** => string [default/example = "1970-01-01T00:00:00Z"]
- **last_updated_at** => string [default/example = "1970-01-01T00:00:00Z"]
- **last_stats_post** => string [default/example = "1970-01-01T00:00:00Z"]
- **long_description** => string [default/example = "blah blah blah"]
- **long_description_raw** => string [default/example = "blah blah blah unsanitized"]
- **long_description_type** => i32 [default/example = 1]
- **guild_count** => i64 [default/example = 0]
- **shard_count** => i64 [default/example = 493]
- **user_count** => i64 [default/example = 0]
- **shards** => (Array) 
- **prefix** => (Optional) string [default/example = "Some prefix, null = slash command"]
- **library** => string [default/example = ""]
- **invite** => (Optional) string [default/example = "Raw invite, null = auto-generated. Use invite_link instead"]
- **invite_link** => string [default/example = "https://discord.com/api/oauth2/authorize...."]
- **invite_amount** => i32 [default/example = 48]
- **owners** => (Array) Struct BotOwner 
	- **user** => Struct User 
		- **id** => string [default/example = ""]
		- **username** => string [default/example = ""]
		- **disc** => string [default/example = ""]
		- **avatar** => string [default/example = ""]
		- **bot** => bool [default/example = false]
		- **status** => string [default/example = "Unknown"]



	- **main** => bool [default/example = false]



- **owners_html** => string [default/example = ""]
- **features** => (Array) Struct Feature 
	- **id** => string [default/example = ""]
	- **name** => string [default/example = ""]
	- **viewed_as** => string [default/example = ""]
	- **description** => string [default/example = ""]



- **state** => i32 [default/example = 0]
- **page_style** => i32 [default/example = 1]
- **website** => (Optional) string [default/example = "https://example.com"]
- **support** => (Optional) string [default/example = ""]
- **github** => (Optional) string [default/example = "https://github.com/Fates-List/FatesList"]
- **css** => string [default/example = "<style></style>"]
- **votes** => i64 [default/example = 0]
- **total_votes** => i64 [default/example = 0]
- **vanity** => string [default/example = ""]
- **donate** => (Optional) string [default/example = "https://paypal.me/example"]
- **privacy_policy** => (Optional) string [default/example = "https://lynx.fateslist.xyz/frostpaw/tos"]
- **nsfw** => bool [default/example = false]
- **banner_card** => (Optional) string [default/example = "https://api.fateslist.xyz/static/botlisticon.webp"]
- **banner_page** => (Optional) string [default/example = "https://api.fateslist.xyz/static/botlisticon.webp"]
- **keep_banner_decor** => bool [default/example = false]
- **client_id** => string [default/example = ""]
- **flags** => (Array) 
- **action_logs** => (Array) Struct ActionLog 
	- **user_id** => string [default/example = ""]
	- **bot_id** => string [default/example = ""]
	- **action** => i32 [default/example = 0]
	- **action_time** => string [default/example = "1970-01-01T00:00:00Z"]
	- **context** => (Optional) string [default/example = "Some context as to why the action happened"]



- **vpm** => (Optional) (Array) Struct VotesPerMonth 
	- **votes** => i64 [default/example = 0]
	- **ts** => string [default/example = "1970-01-01T00:00:00Z"]



- **uptime_checks_total** => (Optional) i32 [default/example = 30]
- **uptime_checks_failed** => (Optional) i32 [default/example = 19]
- **commands** => - **default** => (Array) Struct BotCommand 
	- **cmd_type** => i32 [default/example = 0]
	- **groups** => (Array) 
	- **name** => string [default/example = ""]
	- **vote_locked** => bool [default/example = false]
	- **description** => string [default/example = ""]
	- **args** => (Array) 
	- **examples** => (Array) 
	- **premium_only** => bool [default/example = false]
	- **notes** => (Array) 
	- **doc_link** => None (unknown value type)
	- **id** => None (unknown value type)
	- **nsfw** => bool [default/example = false]





- **resources** => (Array) Struct Resource 
	- **id** => None (unknown value type)
	- **resource_title** => string [default/example = ""]
	- **resource_link** => string [default/example = ""]
	- **resource_description** => string [default/example = ""]



- **webhook** => (Optional) string [default/example = "This will be redacted for Get Bot endpoint"]
- **webhook_secret** => (Optional) string [default/example = "This (along with ``webhook_type``, ``api_token`` and ``webhook_hmac_only``) will be redacted for Get Bot endpoint"]
- **webhook_type** => None (unknown value type)
- **webhook_hmac_only** => None (unknown value type)
- **api_token** => (Optional) string [default/example = "This will be redacted for Get Bot endpoint"]



**Request Body Example**

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
    "prefix": "Some prefix, null = slash command",
    "library": "",
    "invite": "Raw invite, null = auto-generated. Use invite_link instead",
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
    "website": "https://example.com",
    "support": "",
    "github": "https://github.com/Fates-List/FatesList",
    "css": "<style></style>",
    "votes": 0,
    "total_votes": 0,
    "vanity": "",
    "donate": "https://paypal.me/example",
    "privacy_policy": "https://lynx.fateslist.xyz/frostpaw/tos",
    "nsfw": false,
    "banner_card": "https://api.fateslist.xyz/static/botlisticon.webp",
    "banner_page": "https://api.fateslist.xyz/static/botlisticon.webp",
    "keep_banner_decor": false,
    "client_id": "",
    "flags": [],
    "action_logs": [
        {
            "user_id": "",
            "bot_id": "",
            "action": 0,
            "action_time": "1970-01-01T00:00:00Z",
            "context": "Some context as to why the action happened"
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
                "doc_link": null,
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
    "webhook_secret": "This (along with ``webhook_type``, ``api_token`` and ``webhook_hmac_only``) will be redacted for Get Bot endpoint",
    "webhook_type": null,
    "webhook_hmac_only": null,
    "api_token": "This will be redacted for Get Bot endpoint"
}
```

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://lynx.fateslist.xyz/docs/endpoints#authorization)


### Transfer Ownership
#### PATCH /users/{user_id}/bots/{bot_id}/main-owner


Transfers bot ownership.

You **must** be main owner to use this endpoint.


**Path parameters**

- **user_id** => i64 [default/example = 0]
- **bot_id** => i64 [default/example = 0]



**Query parameters**




**Request Body Description**

- **user** => Struct User 
	- **id** => string [default/example = "id here"]
	- **username** => string [default/example = "Leave blank"]
	- **disc** => string [default/example = "Leave blank"]
	- **avatar** => string [default/example = "Leave blank"]
	- **bot** => bool [default/example = false]
	- **status** => string [default/example = "Unknown"]



- **main** => bool [default/example = true]



**Request Body Example**

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

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://lynx.fateslist.xyz/docs/endpoints#authorization)


### Delete Bot
#### DELETE /users/{user_id}/bots/{bot_id}


Deletes a bot.

You **must** be main owner to use this endpoint.


**Path parameters**

- **user_id** => i64 [default/example = 0]
- **bot_id** => i64 [default/example = 0]



**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://lynx.fateslist.xyz/docs/endpoints#authorization)


### Get Import Sources
#### GET /import-sources


Returns a array of sources that a bot can be imported from.


**Path parameters**




**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **sources** => (Array) Struct ImportSourceListItem 
	- **id** => string [default/example = "Rdl"]
	- **name** => string [default/example = "Rovel Bot List"]






**Response Body Example**

```json
{
    "sources": [
        {
            "id": "Rdl",
            "name": "Rovel Bot List"
        }
    ]
}
```
**Authorization Needed** | 


### Import Bot
#### POST /users/{user_id}/bots/{bot_id}/import?src={source}


Imports a bot from a source listed in ``Get Import Sources``.


**Path parameters**

- **user_id** => i64 [default/example = 0]
- **bot_id** => i64 [default/example = 0]



**Query parameters**

- **src** => string [default/example = "Rdl"]



**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://lynx.fateslist.xyz/docs/endpoints#authorization)


## Appeal

### New Appeal
#### POST /users/{user_id}/bots/{bot_id}/appeal


Creates a appeal/request for a bot.

``request_type`` is a [BotRequestType](https://lynx.fateslist.xyz/docs/enums-ref#botrequesttype)

**Ideally only useful for custom clients**


**Path parameters**

- **user_id** => i64 [default/example = 0]
- **bot_id** => i64 [default/example = 0]



**Query parameters**




**Request Body Description**

- **request_type** => i32 [default/example = 0]
- **appeal** => string [default/example = "This bot deserves to be unbanned because..."]



**Request Body Example**

```json
{
    "request_type": 0,
    "appeal": "This bot deserves to be unbanned because..."
}
```

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://lynx.fateslist.xyz/docs/endpoints#authorization)


## Packs

### Add Pack
#### GET /users/{id}/packs


Creates a bot pack. 

- Set ``id`` to empty string, 
- Set ``created_at`` to any datetime
- In user and bot, only ``id`` must be filled, all others can be left empty string
but must exist in the object


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**




**Request Body Description**

- **id** => string [default/example = "0"]
- **name** => string [default/example = ""]
- **description** => string [default/example = ""]
- **icon** => string [default/example = ""]
- **banner** => string [default/example = ""]
- **resolved_bots** => (Array) Struct ResolvedPackBot 
	- **user** => Struct User 
		- **id** => string [default/example = ""]
		- **username** => string [default/example = ""]
		- **disc** => string [default/example = ""]
		- **avatar** => string [default/example = ""]
		- **bot** => bool [default/example = false]
		- **status** => string [default/example = "Unknown"]



	- **description** => string [default/example = ""]



- **owner** => Struct User 
	- **id** => string [default/example = ""]
	- **username** => string [default/example = ""]
	- **disc** => string [default/example = ""]
	- **avatar** => string [default/example = ""]
	- **bot** => bool [default/example = false]
	- **status** => string [default/example = "Unknown"]



- **created_at** => string [default/example = "1970-01-01T00:00:00Z"]



**Request Body Example**

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

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://lynx.fateslist.xyz/docs/endpoints#authorization)


## Users

### Get Profile
#### GET /profiles/{id}


Gets a user profile.


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **user** => Struct User 
	- **id** => string [default/example = ""]
	- **username** => string [default/example = ""]
	- **disc** => string [default/example = ""]
	- **avatar** => string [default/example = ""]
	- **bot** => bool [default/example = false]
	- **status** => string [default/example = "Unknown"]



- **bots** => (Array) 
- **description_raw** => string [default/example = ""]
- **description** => string [default/example = ""]
- **profile_css** => string [default/example = ""]
- **user_css** => string [default/example = ""]
- **vote_reminder_channel** => (Optional) string [default/example = "939123825885474898"]
- **packs** => (Array) 
- **state** => i32 [default/example = 0]
- **site_lang** => string [default/example = ""]
- **action_logs** => (Array) Struct ActionLog 
	- **user_id** => string [default/example = ""]
	- **bot_id** => string [default/example = ""]
	- **action** => i32 [default/example = 0]
	- **action_time** => string [default/example = "1970-01-01T00:00:00Z"]
	- **context** => (Optional) string [default/example = "Some context as to why the action happened"]



- **user_experiments** => (Array) 



**Response Body Example**

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
    "description_raw": "",
    "description": "",
    "profile_css": "",
    "user_css": "",
    "vote_reminder_channel": "939123825885474898",
    "packs": [],
    "state": 0,
    "site_lang": "",
    "action_logs": [
        {
            "user_id": "",
            "bot_id": "",
            "action": 0,
            "action_time": "1970-01-01T00:00:00Z",
            "context": "Some context as to why the action happened"
        }
    ],
    "user_experiments": []
}
```
**Authorization Needed** | 


### Update Profile
#### PATCH /profiles/{id}


Edits a user profile.

``user`` can be completely empty valued but the keys present in a User must
be present


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**




**Request Body Description**

- **user** => Struct User 
	- **id** => string [default/example = ""]
	- **username** => string [default/example = ""]
	- **disc** => string [default/example = ""]
	- **avatar** => string [default/example = ""]
	- **bot** => bool [default/example = false]
	- **status** => string [default/example = "Unknown"]



- **bots** => (Array) 
- **description_raw** => string [default/example = ""]
- **description** => string [default/example = ""]
- **profile_css** => string [default/example = ""]
- **user_css** => string [default/example = ""]
- **vote_reminder_channel** => (Optional) string [default/example = "939123825885474898"]
- **packs** => (Array) 
- **state** => i32 [default/example = 0]
- **site_lang** => string [default/example = ""]
- **action_logs** => (Array) Struct ActionLog 
	- **user_id** => string [default/example = ""]
	- **bot_id** => string [default/example = ""]
	- **action** => i32 [default/example = 0]
	- **action_time** => string [default/example = "1970-01-01T00:00:00Z"]
	- **context** => (Optional) string [default/example = "Some context as to why the action happened"]



- **user_experiments** => (Array) 



**Request Body Example**

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
    "description_raw": "",
    "description": "",
    "profile_css": "",
    "user_css": "",
    "vote_reminder_channel": "939123825885474898",
    "packs": [],
    "state": 0,
    "site_lang": "",
    "action_logs": [
        {
            "user_id": "",
            "bot_id": "",
            "action": 0,
            "action_time": "1970-01-01T00:00:00Z",
            "context": "Some context as to why the action happened"
        }
    ],
    "user_experiments": []
}
```

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://lynx.fateslist.xyz/docs/endpoints#authorization)


### Put User Roles
#### PUT /profiles/{id}/roles


Gives user roles on the Fates List support server


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **bot_developer** => bool [default/example = false]
- **certified_developer** => bool [default/example = false]



**Response Body Example**

```json
{
    "bot_developer": false,
    "certified_developer": false
}
```
**Authorization Needed** | [User](https://lynx.fateslist.xyz/docs/endpoints#authorization)


## Reviews

### Get Reviews
#### GET /reviews/{id}


Gets reviews for a reviewable entity.

A reviewable entity is currently only a bot or a server. Profile reviews are a possibility
in the future.

``target_type`` is a [TargetType](https://lynx.fateslist.xyz/docs/enums-ref#targettype)

This reviewable entities id which is a ``i64`` is the id that is specifed in the
path.

``page`` must be greater than 0 or omitted (which will default to page 1).

``user_id`` is optional for this endpoint but specifying it will provide ``user_reviews`` if
the user has made a review. This will tell you the users review for the entity.

``per_page`` (amount of root/non-reply reviews per page) is currently set to 9. 
This may change in the future and is given by ``per_page`` key.

``from`` contains the index/count of the first review of the page.


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**

- **target_type** => i32 [default/example = 0]
- **page** => (Optional) i32 [default/example = 1]
- **user_id** => (Optional) i64 [default/example = 0]



**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **reviews** => (Array) Struct Review 
	- **id** => None (unknown value type)
	- **star_rating** => string [default/example = "0"]
	- **review_text** => string [default/example = ""]
	- **votes** => Struct ParsedReviewVotes 
		- **upvotes** => (Array) 
		- **downvotes** => (Array) 



	- **flagged** => bool [default/example = false]
	- **user** => Struct User 
		- **id** => string [default/example = ""]
		- **username** => string [default/example = ""]
		- **disc** => string [default/example = ""]
		- **avatar** => string [default/example = ""]
		- **bot** => bool [default/example = false]
		- **status** => string [default/example = "Unknown"]



	- **epoch** => (Array) 
	- **replies** => (Array) 
	- **parent_id** => None (unknown value type)



- **per_page** => i64 [default/example = 9]
- **from** => i64 [default/example = 0]
- **stats** => Struct ReviewStats 
	- **average_stars** => string [default/example = "8.800000"]
	- **total** => i64 [default/example = 78]



- **user_review** => (Optional) Struct Review 
	- **id** => None (unknown value type)
	- **star_rating** => string [default/example = "0"]
	- **review_text** => string [default/example = ""]
	- **votes** => Struct ParsedReviewVotes 
		- **upvotes** => (Array) 
		- **downvotes** => (Array) 



	- **flagged** => bool [default/example = false]
	- **user** => Struct User 
		- **id** => string [default/example = ""]
		- **username** => string [default/example = ""]
		- **disc** => string [default/example = ""]
		- **avatar** => string [default/example = ""]
		- **bot** => bool [default/example = false]
		- **status** => string [default/example = "Unknown"]



	- **epoch** => (Array) 
	- **replies** => (Array) 
	- **parent_id** => None (unknown value type)






**Response Body Example**

```json
{
    "reviews": [
        {
            "id": null,
            "star_rating": "0",
            "review_text": "",
            "votes": {
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
        "star_rating": "0",
        "review_text": "",
        "votes": {
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

The ``parent_id`` is optional and is used to create a reply to a review.

``target_type`` is a [TargetType](https://lynx.fateslist.xyz/docs/enums-ref#targettype)

``review`` is a [Review](https://lynx.fateslist.xyz/docs/models-ref#review)

``user_id`` is *required* for this endpoint and must be the user making the review. It must
also match the user token sent in the ``Authorization`` header


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**

- **target_type** => i32 [default/example = 0]
- **page** => None (unknown value type)
- **user_id** => (Optional) i64 [default/example = 0]



**Request Body Description**

- **id** => None (unknown value type)
- **star_rating** => string [default/example = "0"]
- **review_text** => string [default/example = ""]
- **votes** => Struct ParsedReviewVotes 
	- **upvotes** => (Array) 
	- **downvotes** => (Array) 



- **flagged** => bool [default/example = false]
- **user** => Struct User 
	- **id** => string [default/example = ""]
	- **username** => string [default/example = ""]
	- **disc** => string [default/example = ""]
	- **avatar** => string [default/example = ""]
	- **bot** => bool [default/example = false]
	- **status** => string [default/example = "Unknown"]



- **epoch** => (Array) 
- **replies** => (Array) 
- **parent_id** => (Optional) string [default/example = "3b3752ee-f91e-4193-b1ee-edbc677cc9f5"]



**Request Body Example**

```json
{
    "id": null,
    "star_rating": "0",
    "review_text": "",
    "votes": {
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
    "parent_id": "3b3752ee-f91e-4193-b1ee-edbc677cc9f5"
}
```

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://lynx.fateslist.xyz/docs/endpoints#authorization)


### Edit Review
#### PATCH /reviews/{id}


Edits a review.

``page`` should be set to null or omitted though are ignored by this endpoint
so there should not be an error even if provided.

A reviewable entity is currently only a bot or a server. Profile reviews are a possibility
in the future.

``target_type`` is a [TargetType](https://lynx.fateslist.xyz/docs/enums-ref#targettype)

This reviewable entities id which is a ``i64`` is the id that is specifed in the
path.

The id of the review must be specified as ``id`` in the request body which accepts a ``Review``
object. The ``user_id`` specified must *own*/have created the review being editted. Staff should
edit reviews using Lynx when required.

``user_id`` is *required* for this endpoint and must be the user making the review. It must
also match the user token sent in the ``Authorization`` header


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**

- **target_type** => i32 [default/example = 0]
- **page** => None (unknown value type)
- **user_id** => (Optional) i64 [default/example = 0]



**Request Body Description**

- **id** => (Optional) string [default/example = "299cbdcc-16ac-481f-b93c-a659579c4a0b"]
- **star_rating** => string [default/example = "0"]
- **review_text** => string [default/example = ""]
- **votes** => Struct ParsedReviewVotes 
	- **upvotes** => (Array) 
	- **downvotes** => (Array) 



- **flagged** => bool [default/example = false]
- **user** => Struct User 
	- **id** => string [default/example = ""]
	- **username** => string [default/example = ""]
	- **disc** => string [default/example = ""]
	- **avatar** => string [default/example = ""]
	- **bot** => bool [default/example = false]
	- **status** => string [default/example = "Unknown"]



- **epoch** => (Array) 
- **replies** => (Array) 
- **parent_id** => None (unknown value type)



**Request Body Example**

```json
{
    "id": "299cbdcc-16ac-481f-b93c-a659579c4a0b",
    "star_rating": "0",
    "review_text": "",
    "votes": {
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

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://lynx.fateslist.xyz/docs/endpoints#authorization)


### Delete Review
#### DELETE /reviews/{rid}


Deletes a review

``rid`` must be a valid uuid.

``user_id`` is *required* for this endpoint and must be the user making the review. It must
also match the user token sent in the ``Authorization`` header. ``page`` is currently ignored

A reviewable entity is currently only a bot or a server. Profile reviews are a possibility
in the future.

``target_type`` is a [TargetType](https://lynx.fateslist.xyz/docs/enums-ref#targettype)

``target_type`` is not currently checked but it is a good idea to set it anyways. You must
set this anyways so you might as well set it correctly.


**Path parameters**

- **rid** => string [default/example = "89d20615-04d3-46e1-b8fe-e6a566be072f"]



**Query parameters**

- **target_type** => i32 [default/example = 0]
- **page** => None (unknown value type)
- **user_id** => (Optional) i64 [default/example = 0]



**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://lynx.fateslist.xyz/docs/endpoints#authorization)


### Vote Review
#### PATCH /reviews/{rid}/votes


Creates a vote for a review

``rid`` must be a valid uuid.

``user_id`` is *required* for this endpoint and must be the user making the review. It must
also match the user token sent in the ``Authorization`` header. 

**Unlike other review APIs, ``user_id`` here is in request body as ReviewVote object**

A reviewable entity is currently only a bot or a server. Profile reviews are a possibility
in the future.

``target_type`` is a [TargetType](https://lynx.fateslist.xyz/docs/enums-ref#targettype)

**This endpoint does not require ``target_type`` at all. You can safely omit it**


**Path parameters**

- **rid** => string [default/example = "ad7227f1-9fd0-487a-a08b-f91ee4709954"]



**Query parameters**




**Request Body Description**

- **user_id** => string [default/example = "user id here"]
- **upvote** => bool [default/example = true]



**Request Body Example**

```json
{
    "user_id": "user id here",
    "upvote": true
}
```

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [User](https://lynx.fateslist.xyz/docs/endpoints#authorization)


## Stats

### Get List Stats
#### GET /stats


Returns the bot list stats. This currently returns the full list of all bots
as a vector/list of IndexBot structs.

As a client, it is your responsibility, to parse this. Pagination may be added
if the list grows and then requires it.


**Path parameters**




**Query parameters**




**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **total_bots** => i64 [default/example = 0]
- **total_servers** => i64 [default/example = 0]
- **total_users** => i64 [default/example = 0]
- **bots** => (Array) Struct IndexBot 
	- **guild_count** => i64 [default/example = 0]
	- **description** => string [default/example = ""]
	- **banner** => string [default/example = ""]
	- **nsfw** => bool [default/example = false]
	- **votes** => i64 [default/example = 0]
	- **state** => i32 [default/example = 0]
	- **user** => Struct User 
		- **id** => string [default/example = ""]
		- **username** => string [default/example = ""]
		- **disc** => string [default/example = ""]
		- **avatar** => string [default/example = ""]
		- **bot** => bool [default/example = false]
		- **status** => string [default/example = "Unknown"]



	- **flags** => (Array) 



- **servers** => (Array) 
- **uptime** => f64 [default/example = 0]
- **cpu_idle** => f64 [default/example = 0]
- **mem_total** => u64 [default/example = 0]
- **mem_free** => u64 [default/example = 0]
- **mem_available** => u64 [default/example = 0]
- **swap_total** => u64 [default/example = 0]
- **swap_free** => u64 [default/example = 0]
- **mem_dirty** => u64 [default/example = 0]
- **mem_active** => u64 [default/example = 0]
- **mem_inactive** => u64 [default/example = 0]
- **mem_buffers** => u64 [default/example = 0]
- **mem_committed** => u64 [default/example = 0]



**Response Body Example**

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

``target_type`` is a [TargetType](https://lynx.fateslist.xyz/docs/enums-ref#targettype)


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**

- **target_type** => i32 [default/example = 0]



**Request Body Description**

- **id** => None (unknown value type)
- **resource_title** => string [default/example = ""]
- **resource_link** => string [default/example = ""]
- **resource_description** => string [default/example = ""]



**Request Body Example**

```json
{
    "id": null,
    "resource_title": "",
    "resource_link": "",
    "resource_description": ""
}
```

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [Bot](https://lynx.fateslist.xyz/docs/endpoints#authorization), [Server](https://lynx.fateslist.xyz/docs/endpoints#authorization)


### Delete Resource
#### DELETE /resources/{id}


Deletes a resource. Both bots and servers support these however only bots 
support the frontend resource creator in Bot Settings as of right now.

The ``id`` here must be the resource id

``target_type`` is a [TargetType](https://lynx.fateslist.xyz/docs/enums-ref#targettype)


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**

- **id** => string [default/example = "10aa772f-cdcc-4a95-b2bf-10ba2f5238a6"]
- **target_type** => i32 [default/example = 0]



**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [Bot](https://lynx.fateslist.xyz/docs/endpoints#authorization), [Server](https://lynx.fateslist.xyz/docs/endpoints#authorization)


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

``target_type`` is a [TargetType](https://lynx.fateslist.xyz/docs/enums-ref#targettype)


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**

- **target_type** => i32 [default/example = 0]



**Request Body Description**

- **commands** => (Array) Struct BotCommand 
	- **cmd_type** => i32 [default/example = 0]
	- **groups** => (Array) 
	- **name** => string [default/example = ""]
	- **vote_locked** => bool [default/example = false]
	- **description** => string [default/example = ""]
	- **args** => (Array) 
	- **examples** => (Array) 
	- **premium_only** => bool [default/example = false]
	- **notes** => (Array) 
	- **doc_link** => None (unknown value type)
	- **id** => None (unknown value type)
	- **nsfw** => bool [default/example = false]






**Request Body Example**

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
            "doc_link": null,
            "id": null,
            "nsfw": false
        }
    ]
}
```

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [Bot](https://lynx.fateslist.xyz/docs/endpoints#authorization)


### Delete Bot Command
#### DELETE /bots/{id}/commands


DELETE a command.

The ``id`` here must be the bot id you wish to add the command for

``names`` and ``ids`` must be a ``|`` seperated list of ``names`` or valid
UUIDs in the case of ids. Bad names/ids will be ignored


**Path parameters**

- **id** => i64 [default/example = 0]



**Query parameters**

- **nuke** => (Optional) bool [default/example = false]
- **names** => (Optional) string [default/example = "command name|command name 2"]
- **ids** => (Optional) string [default/example = "id 1|id 2"]



**Request Body Description**




**Request Body Example**

```json
{}
```

**Response Body Description**

- **done** => bool [default/example = true]
- **reason** => None (unknown value type)
- **context** => None (unknown value type)



**Response Body Example**

```json
{
    "done": true,
    "reason": null,
    "context": null
}
```
**Authorization Needed** | [Bot](https://lynx.fateslist.xyz/docs/endpoints#authorization)


