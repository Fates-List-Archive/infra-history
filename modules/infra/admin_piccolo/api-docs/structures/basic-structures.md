### Terminology

- **Snowflake:** A snowflake is a discord snowflake (user ID) in string format (like "563808552288780322")

### Structures

### BaseUser

A BaseUser represents a user on Fates List (See [https://github.com/Fates-List/FatesList/blob/main/modules/models/enums.py](https://github.com/Fates-List/FatesList/blob/main/modules/models/enums.py), link may change). A User, Bot, BotPartial (index and search page uses this) and ProfilePartial (profile search uses this) object both extend the BaseUser class. This is a basic structure that can be seen everywhere in the Fates List API. Note that all values here are according to our 8 hour redis cache we have setup to avoid being ratelimited.

| Key | Description | Type |
| :--- | :--- | :--- |
| id  | The ID of the user | Snowflake |
| username | The username of the user | String |
| avatar | The avatar URL of the user | String |
| disc | The discriminator | String |
| status | The status of the user | Status (see below) |
| bot | Whether the user is a bot or not | Boolean |

### Status

Fates List also records the users status as well. This is internally an integer to save space and to decrease API response time, we use the same internal values in our API too.

| Status Number | Corresponding Status |
| :--- | :--- |
| 0 | Unknown Status |
| 1 | Online |
| 2 | Offline/Invisible |
| 3 | Idle |
| 4 | Do Not Disturb |

### Bot State

Fates List has an advanced moderation system based on something called a state. Every bot has a state which is an integer which dictates what the current state of the bot is, whether it is banned, in queue, under review, certified etc. and more. It is the most important attribute about a bot on Fates List. Users and servers have this as well

| State Number | Corresponding State |
| :--- | :--- |
| 0 | Verified/Approved |
| 1 | In Queue |
| 2 | Denied |
| 3 | Hidden/Private (internal, only settable by staff) |
| 4 | Banned |
| 5 | Under Review (set by running +claim in Test Server by staff) |
| 6 | Certified |
| 7 | Archived (set to read only by owner) |

### User State

Similar to a bot, users have state as well:

| State Number | Corresponding State |
| :--- | :--- |
| 0 | Normal |
| 1 | Global Ban |
| 2 | Login Ban |
| 3 | Profile Edit Ban |
| 4 | Data Deletion Request Ban (not possible to get in the API however) |

### Partial Objects

While these are not a “basic structure”, they are still fundemental to the Fates List API, if you see the schema for Fates List, you will notice multiple *Partial schemas. These schemas mean that they are partial or incomplete objects. An example is add bot, where a BotMeta (which is a partial object) is used, fields here may be different from the main due to lack of information and so should be seperate types when you code for the Fates List API.
