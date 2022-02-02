# Server List Infrastructure And Bot

## How it works

Each bot on flamepaw contains a function called cmdInit which creates a IR (types.SlashCommamd). 

The *actual* command is usually a expanded set that is compressed to the types.SlashCommand IR.

**Example**: admin.AdminOP and serverlist.ServerListCommand

The Handler on IR is usually a hook that does common checks beforehand before calling the commands handler

The context is a common types.SlashContext