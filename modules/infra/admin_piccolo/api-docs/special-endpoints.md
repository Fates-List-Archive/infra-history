Below are some core endpoints for bots to use in case you're scared of the main ``Endpoints`` documentation

**This does not cover every endpoint in the ``Endpoints`` documentation. Things like Bot Commands, Resources, Get Bot and other API's are documented inside ``Endpoints`` and *not* here however all things within this page are also on ``Endpoints`` and may be more up to date with new (constantly evolving) fields. The fields present here are stabilized and may be different as such from ``Endpoints`` which may have new fields**

### Post Bot Stats

This endpoint *should* be used by bots to post stats for their list

```
https://api.fateslist.xyz/bots/{bot_id}/stats
```

**Method:** POST

#### Example:

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

**This requires** [Bot](https://docs.fateslist.xyz/endpoints#authorization) API token to be specified.

### Get User Votes

This endpoint may be slightly unreliable at this time. It is recommended to use WebSockets instead

Endpoint to check amount of votes a user has.

- votes | The amount of votes the bot has.
- voted | Whether or not the user has *ever* voted for the bot.
- timestamps | A list of timestamps that the user has voted for the bot on that has been recorded.
- expiry | The time when the user can next vote.
- vote_right_now | Whether a user can vote right now. Currently equivalent to `vote_epoch < 0`.

```
https://api.fateslist.xyz/users/{user_id}/bots/{bot_id}/votes
```

**Method:** GET

**Response Body**

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

No authorization is required