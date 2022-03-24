### Server Listing Help

If you're reading this, you probably already know what server listing (and slash commands) are. This guide will not go over that

### Slash command syntax

This guide will use the following syntax for slash commands: ``/command option:foo anotheroption:bar``. To specify a list of values (where supported), use ``|``. Currently only Autovote Roles supports this

### How do I add my server?

Good question. Your server should usually be automatically added for you once you add the bot to your server. Just set a description using ``/set field:Description value:My lovely description``. If you do not do so, the description will be randomly set for you and it will likely not be what you want. You should set a long description using ``/set field:Long Description`` value:My really really long description. For really long descriptions, you can also create a paste on **pastebin** and provide the pastebin link as the value

### What is the 'State' option?

Another good question. Long story short, state allows you to configure the privacy of your server and in the future may do other things as well. What is this privacy, you ask? Well, if you are being raided and you wish to stop people from joining your server during a raid, then you can simply set the state of your server to ``private_viewable`` or ``8``. This will stop it from being indexed and will also block users from joining your server until you're ready to set the state to ``public`` or ``0``.

### Vote Rewards

You can reward users for voting for your server using vote rewards. This can be things like custom roles or extra perks! In order to use vote rewards, you will need to use our websocket API to listen for events. Once you have gotten a server vote event, you can then give rewards for voting. The event number for server votes is 71 (may change).

*All users using server listing vote webhooks should note that these are being removed for now. Use websockets instead until a new webhook system is made (if ever).*

### Server Allow List

For invite-only servers, you can/should use a user whitelist to prevent users outside the user whitelist from joining your server. If you do not have 'Whitelist Only' set on your server, anyone may join it. User blacklists allow you to blacklist bad users from getting an invite to your server via Fates List. Use ``/allowlist`` to configure the allow list. The commands will provide help if you need it.

### Server Tags

Server Tags on Fates List are a great way to allow similar users to find your server! The first server to make a tag is given ownership over that tag. **Tag owners can control the iconify emoji of the tag however they cannot remove the tag from their server without transferring it to another server**. *Flamepaw (staff server) is the default server a tag will transfer to during a transfer unless a server is explicitly mentioned*. Tags should be compelling and quickly describe the server. Creating a new similar tag just to gain ownership of it may result in a ban from server listing. Tags shoild also be short and a maximum of 20 characters in length. Some keywords are not allowed/reserved as well.

The default tag is ``fluent:animal-cat-28-regular``.

### Updates from previous versions

For anyone using Fates List Server Listing beforehand, some privacy changes

1. User Whitelist now overrides private setting
2. 'Server Whitelist' was added
3. whitelist only implies login_required
4. whitelist overrides blacklist