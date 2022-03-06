# Enum Reference

Below is a reference of all the enums used in Fates List, It is automatically generated

## APIEvents

May or may not be in numeric order

| Name | Value | Description |
| :--- | :--- | :--- |
| bot_vote | 0 | Vote Bot Event |
| bot_add | 1 | Bot Add Event |
| bot_edit | 2 | Bot Edit Event |
| bot_delete | 3 | Bot Delete Event |
| bot_claim | 4 | Bot Claim Event |
| bot_approve | 5 | Bot Approve Event |
| bot_deny | 6 | Bot Deny Event |
| bot_ban | 7 | Bot Ban Event |
| bot_unban | 8 | Bot Unban Event |
| bot_requeue | 9 | Bot Requeue Event |
| bot_certify | 10 | Bot Certify Event |
| bot_uncertify | 11 | Bot Uncertify Event |
| bot_transfer | 12 | Bot Ownership Transfer Event |
| bot_hide | 13 | Bot Hide Event |
| bot_archive | 14 | Bot Archive Event |
| bot_unverify | 15 | Bot Unverify Event |
| bot_view | 16 | Bot View Event (Websocket only) |
| bot_invite | 17 | Bot Invite Event (Websocket only) |
| bot_unclaim | 18 | Bot Unclaim Event |
| bot_root_update | 19 | Bot Root State Update Event |
| bot_vote_reset | 20 | Bot Votes Reset Event |
| bot_vote_reset_all | 21 | Bot Votes Reset All Event |
| bot_lock | 22 | Bot Lock Event |
| bot_unlock | 23 | Bot Unlock Event |
| review_vote | 30 | Review Vote Event |
| review_add | 31 | Bot Review Add Event |
| review_edit | 32 | Bot Review Edit Event |
| review_delete | 33 | Bot Review Delete Event |
| resource_add | 40 | Bot Resource Add Event |
| resource_delete | 41 | Bot Resource Delete Event |
| command_add | 50 | Bot Command Add Event |
| command_delete | 51 | Bot Command Delete Event |
| server_view | 70 | Server View Event |
| server_vote | 71 | Server Vote Event |
| server_invite | 72 | Server Invite Event |
| staff_lock | 80 | Staff Lock |
| staff_unlock | 81 | Staff Unlock |


## BotAdminOp

Handles bot admin operations

| Name | Value | Description | Perm | Reason Needed | Recursive | Cooldown |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| requeue | REQUEUE | Requeue Bot | 3 | True | False | CooldownBucket.requeue (12.0) |
| claim | CLAIM | Claim Bot | 2 | False | False | None |
| unclaim | UNCLAIM | Unclaim Bot | 2 | False | False | None |
| ban | BAN | Ban Bot | 3 | True | False | CooldownBucket.ban (18.0) |
| unban | UNBAN | Unban Bot | 3 | True | False | CooldownBucket.ban (18.0) |
| certify | CERTIFY | Certify Bot | 5 | False | False | None |
| uncertify | UNCERTTIFY | Uncertify Bot | 5 | True | False | None |
| approve | APPROVE | Approve Bot | 2 | True | False | None |
| deny | DENY | Deny Bot | 2 | True | False | None |
| unverify | UNVERIFY | Unverify Bot | 3 | True | False | CooldownBucket.ban (18.0) |
| reset_votes | RESETVOTES | Reset All Votes | (5, 7) | True | True | CooldownBucket.reset (60) |
| staff_lock | STAFFLOCK | Staff Lock Bot | 4 | True | False | None |
| staff_unlock | STAFFUNLOCK | Staff Unlock Bot | 4 | True | False | CooldownBucket.lock (120) |
| bot_lock | BLOCK | Bot Lock | 0 | False | False | None |
| bot_unlock | BUNLOCK | Bot Unlock | 4 | False | False | CooldownBucket.lock (120) |


## BotFlag

| Name | Value | Description |
| :--- | :--- | :--- |
| unlocked | 0 | Bot unlocked for editing |
| edit_locked | 1 | Bot locked for editing |
| staff_locked | 2 | Bot locked by staff |
| stats_locked | 3 | Stats locked |
| vote_locked | 4 | Vote locked |
| system | 5 | System bot |


## BotRequestType

| Name | Value | Description |
| :--- | :--- | :--- |
| appeal | 0 | Bot |
| certification | 1 | Certification |


## BotState

| Name | Value | Description |
| :--- | :--- | :--- |
| approved | 0 | Verified |
| pending | 1 | Pending Verification |
| denied | 2 | Denied |
| hidden | 3 | Hidden |
| banned | 4 | Banned |
| under_review | 5 | Under Review |
| certified | 6 | Certified |
| archived | 7 | Archived |
| private_viewable | 8 | Private, but viewable with link (server only) |
| private_staff_only | 9 | Private, only staff may join (server only) |


## CommandType


    0 - Regular (Prefix) Command

    1 - Slash Command (Guild)
    
    2 - Slash Command (Global)
    

| Name | Value | Description |
| :--- | :--- | :--- |
| regular | 0 | Regular Command |
| guild_slash | 1 | Slash Command (guild) |
| global_slash | 2 | Slash Command (global) |


## CooldownBucket

| Name | Value | Description |
| :--- | :--- | :--- |
| requeue | 12.0 | An enumeration. |
| ban | 18.0 | An enumeration. |
| transfer | 30.0 | An enumeration. |
| reset | 60 | An enumeration. |
| lock | 120 | An enumeration. |
| delete | 210.0 | An enumeration. |


## LongDescType

| Name | Value | Description |
| :--- | :--- | :--- |
| html | 0 | HTML/Raw Description |
| markdown_pymarkdown | 1 | Markdown using Python Markdown |
| markdown_marked | 2 | Markdown using JavaScript Marked |


## PageStyle

| Name | Value | Description |
| :--- | :--- | :--- |
| tabs | 0 | Tabs |
| single_scroll | 1 | Single Scroll |


## PromotionType

| Name | Value | Description |
| :--- | :--- | :--- |
| announcement | 0 | Announcement |
| promotion | 1 | Promotion |
| generic | 2 | Generic |


## ReviewType

| Name | Value | Description |
| :--- | :--- | :--- |
| bot | 0 | Bot |
| server | 1 | Server |


## SearchType

| Name | Value | Description |
| :--- | :--- | :--- |
| bot | bot | Bot |
| server | server | Server |
| profile | profile | Profile |
| pack | pack | Bot Pack |


## SiteLang

Site languages

| Name | Value | Description |
| :--- | :--- | :--- |
| en | en | English |
| es | es | Spanish |
| fr | fr | France |
| hi | hi | Hindi |
| ru | ru | Russian |


## Status

Status object (See https://docs.fateslist.xyz/basics/basic-structures#status for more information)

| Name | Value | Description |
| :--- | :--- | :--- |
| unknown | 0 | Unknown |
| online | 1 | Online |
| offline | 2 | Offline |
| idle | 3 | Idle |
| dnd | 4 | Do Not Disturb |


## UserBotAction

| Name | Value | Description |
| :--- | :--- | :--- |
| approve | 0 | Approve |
| deny | 1 | Deny |
| certify | 2 | Certify |
| ban | 3 | Ban |
| claim | 4 | Claim |
| unclaim | 5 | Unclaim |
| transfer_ownership | 6 | Transfer Bot Ownership |
| edit_bot | 7 | Edit Bot |
| delete_bot | 8 | Delete Bot |


## UserState

| Name | Value | Description | Sitelock |
| :--- | :--- | :--- | :--- |
| normal | 0 | Normal (No Ban) | False |
| global_ban | 1 | Global Ban | True |
| profile_edit_ban | 2 | Profile Edit Ban | False |
| ddr_ban | 3 | Data Deletion Request Ban | True |
| api_ban | 4 | Full API Ban | False |


## Vanity

| Name | Value | Description |
| :--- | :--- | :--- |
| server | 0 | Server |
| bot | 1 | Bot |
| profile | 2 | Profile |


## VanityType

| Name | Value | Description |
| :--- | :--- | :--- |
| bot | bot | Bot |
| guild | guild | Server |


## VoteReminderMode

| Name | Value | Description |
| :--- | :--- | :--- |
| disable | 0 | Disable vote reminders |
| enable | 1 | Enable vote reminders |


## WebhookType

| Name | Value | Description |
| :--- | :--- | :--- |
| vote | 0 | Vote Webhook |
| discord | 1 | Discord Integration |
| fc | 2 | Fates Client (deprecated) |


## WidgetFormat

| Name | Value | Description |
| :--- | :--- | :--- |
| json | json | JSON Widget |
| html | html | HTML Widget |
| png | png | Widget (as png image) |
| webp | webp | Widget (as webp image) |


## WidgetType

| Name | Value | Description |
| :--- | :--- | :--- |
| bot | bot |  |
| server | server |  |

