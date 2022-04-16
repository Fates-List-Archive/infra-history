Below is a reference of all the enums used in Fates List, 
    
It is semi-automatically generated

    
### LongDescriptionType

The type of long description that the bot/server has opted for

**Common JSON keys**

- ``long_description_type``


**Values**

| Name | Value |
| :--- | :--- |
| **Html** | 0 |
| **MarkdownServerSide** | 1 |


    
### State

The state of the bot or server (approved, denied etc.)

**Common JSON keys**

- ``state``


**Values**

| Name | Value |
| :--- | :--- |
| **Approved** | 0 |
| **Pending** | 1 |
| **Denied** | 2 |
| **Hidden** | 3 |
| **Banned** | 4 |
| **UnderReview** | 5 |
| **Certified** | 6 |
| **Archived** | 7 |
| **PrivateViewable** | 8 |
| **PrivateStaffOnly** | 9 |


    
### UserState

The state of the user (normal, banned etc.)

**Common JSON keys**

- ``state``


**Values**

| Name | Value |
| :--- | :--- |
| **Normal** | 0 |
| **GlobalBan** | 1 |
| **ProfileEditBan** | 2 |


    
### Flags

The flags of the bot or server (system bot etc)

**Common JSON keys**

- ``flags``


**Values**

| Name | Value |
| :--- | :--- |
| **Unlocked** | 0 |
| **EditLocked** | 1 |
| **StaffLocked** | 2 |
| **StatsLocked** | 3 |
| **VoteLocked** | 4 |
| **System** | 5 |


    
### UserExperiments

All available user experiments

**Common JSON keys**

- ``user_experiments``


**Values**

| Name | Value |
| :--- | :--- |
| **Unknown** | 0 |
| **GetRolesSelector** | 1 |
| **LynxExperimentRolloutView** | 2 |


    
### Status

The status of the user. **Due to bugs, this currently shows Unknown only but this will be fixed soon!**

**Common JSON keys**

- ``flags``


**Values**

| Name | Value |
| :--- | :--- |
| **Unknown** | "Unknown" |
| **Online** | "Online" |
| **Offline** | "Offline" |
| **Idle** | "Idle" |
| **DoNotDisturb** | "DoNotDisturb" |


    
### CommandType

The type of the command being posted (prefix, guild-only etc)

**Common JSON keys**

- ``cmd_type``


**Values**

| Name | Value |
| :--- | :--- |
| **PrefixCommand** | 0 |
| **SlashCommandGlobal** | 1 |
| **SlashCommandGuild** | 2 |


    
### ImportSource

The source to import bots from

**Common JSON keys**

- ``src (query parameter)``


**Values**

| Name | Value |
| :--- | :--- |
| **Rdl** | "Rdl" |
| **Topgg** | "Topgg" |
| **Ibl** | "Ibl" |
| **Other** | "Other" |


    
### PageStyle

The style/theme of the bot page. Servers always use single-page view

**Common JSON keys**

- ``page_style``


**Values**

| Name | Value |
| :--- | :--- |
| **Tabs** | 0 |
| **SingleScroll** | 1 |


    
### WebhookType

The type of webhook being used

**Common JSON keys**

- ``webhook_type``


**Values**

| Name | Value |
| :--- | :--- |
| **Vote** | 0 |
| **DiscordIntegration** | 1 |
| **DeprecatedFatesClient** | 2 |


    
### EventName

The name of the event being sent and its corresponding number

**Common JSON keys**

- ``e``
- ``...(non-exhaustive list, use context and it should be self-explanatory)``


**Values**

| Name | Value |
| :--- | :--- |
| **BotVote** | 0 |
| **BotEdit** | 2 |
| **BotDelete** | 3 |
| **BotClaim** | 4 |
| **BotApprove** | 5 |
| **BotDeny** | 6 |
| **BotBan** | 7 |
| **BotUnban** | 8 |
| **BotRequeue** | 9 |
| **BotCertify** | 10 |
| **BotUncertify** | 11 |
| **BotTransfer** | 12 |
| **BotUnverify** | 15 |
| **BotView** | 16 |
| **BotInvite** | 17 |
| **BotUnclaim** | 18 |
| **BotVoteReset** | 20 |
| **BotLock** | 22 |
| **BotUnlock** | 23 |
| **ReviewVote** | 30 |
| **ReviewAdd** | 31 |
| **ReviewEdit** | 32 |
| **ReviewDelete** | 33 |
| **ResourceAdd** | 40 |
| **ResourceDelete** | 41 |
| **CommandAdd** | 50 |
| **CommandDelete** | 51 |
| **ServerView** | 70 |
| **ServerVote** | 71 |
| **ServerInvite** | 72 |


    
### UserBotAction

The name of the event being sent and its corresponding number

**Common JSON keys**

- ``action``


**Values**

| Name | Value |
| :--- | :--- |
| **Approve** | 0 |
| **Deny** | 1 |
| **Certify** | 2 |
| **Ban** | 3 |
| **Claim** | 4 |
| **Unclaim** | 5 |
| **TransferOwnership** | 6 |
| **EditBot** | 7 |
| **DeleteBot** | 8 |
| **Unban** | 9 |
| **Uncertify** | 10 |
| **Unverify** | 11 |
| **Requeue** | 12 |


    
### BotRequestType

The type of appeal being sent

**Common JSON keys**

- ``request_type``


**Values**

| Name | Value |
| :--- | :--- |
| **Appeal** | 0 |
| **Certification** | 1 |


    
### TargetType

The type of the entity (bot/server)

**Common JSON keys**

- ``target_type``


**Values**

| Name | Value |
| :--- | :--- |
| **Bot** | 0 |
| **Server** | 1 |

