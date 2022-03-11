### Bot Requirements

These are some requirements we test for and require. Note that this list is **non-inclusive**

<blockquote class="quote">

#### Basics

1. It is perfectly OK to submit bots and servers that are in competition with Fates List (such as API/manager bots of other bot lists with their permission)
2. Your bot may not be a fork or instance of another bot without substantial modifications and prior permission from the owner of the bot you have forked/made an instance of.
3. Your bot should handle errors in a user-friendly way. A way of reporting errors is a nice extra tidbit to have though not strictly required. Giving tracebacks is allowed if it does not leak sensitive information such as bot tokens or private information on a user.
4. Your bot must respect the Discord API and rate-limits. This also means that your bot should not spam messages or be a 'rainbow role' bot.
5. Your bot must follow the Discord ToS and guidelines. This also includes no invite rewards, no nuking etc.
6. Custom bots based of/dependent on/running an instance of another bot such as bot-makers not allowed by discord, BotGhost, MEE6 Premium, Wick VIP is prohibited unless it has unique features that you have added to it and can be configured on other servers by users.
7. For frameworks such as redbot, you must have at least 3 custom-made cogs (or the equivalent for other frameworks). You must give credits to any framework you are using. *BDFD/BDScript/other bot makers are not allowed on Fates List unless it is also allowed by Discord and your bot is high-quality and has features*


</blockquote>

<blockquote class="quote">

#### Commands

1. Your bot must have a working help command
2. If your bot has level messages or welcome messages, it must be optional and disableable
3. Your bot should not DM users when it join unless it needs to DM the *owner* important or sensitive information (such as Wick's rescue key) 
4. Your bot should not DM users when they join a server unless a server manager chooses to enable such a feature. Bots that do need to DM users such as verification bots may be exempt from this rule on a case by case basis
5. All commands of a bot should check user and their own permissions before doing any action. For example, your bot should not kick users unless the user and the bot has the Kick Members permission. *Commands may not be admin locked and NSFW commands must be locked to NSFW channels*
6. Commands must have a purpose (no filler commands). Filler commands are ignored and will make your bot low quality. An example of filler commands/commands with no purpose is a bot with 20 purge commands or commands which are repeated in different ways or serve the same purpose
7. Bots *should* have at least 5 working commands and at least 80% of commands shown in its help command working. If your bot has a really unique feature however, this rule may be reconsidered for your bot.
8. Sensitive commands (such as eval) should be locked to bot owners only. Fates List is not responsible for the code you run or for any arbitary code execution/privilege escalation on your bot.


</blockquote>

<blockquote class="quote">

#### Prefixes

1. Bots with common prefixes (`!`, `?`, `.`, `;`) should have a customizable prefix or they may be muted on the support server. You may change the prefix for just Fates List if you want to and staff can do it for you if you tell them the command.
2. You should use the Customizable Prefix feature in your bots settings to denote whather custom prefixes are supported. This is to make it easier for users to know this
3. Your bot must have an easy way to find its prefix. Some good places for this are on bot mentions and bot status


</blockquote>

<blockquote class="quote">

#### Safety

1. Bots should not mass DM or be malicious in any way such as mass nuke, scam bots, free nitro bots. This also applies to servers as well when server listing is done.
2. DMing staff to ask for your bot to be approved/reviewed is strictly prohibited. Your bot will be denied or banned if you do so. You may however ask staff politely to review/show off your bot on your support server if it needs to be verified.
3. Your bot must not have a copyrighted avatar or username. All assets used in your bot must be either owned by you or with permission from the copyright owner.
4. Abusing Discord (mass creating or deleting channels, mass DM/spam/nuke bots) is strictly prohibited and doing so will get you and/or your bot banned from the list and server.
5. Your bot may not be hosted on Glitch/Repl Free Plan and use a software to ping your project. This is also against Repl/Glitch ToS.
6. Your bot must be online during testing


</blockquote>

<blockquote class="quote">

#### Notes

1. You can always appeal a ban or resubmit your bot. To do so, just login, click your username > My Profile > *your bot* > View and then click the link underneath the ban message to start the ban appeal or resubmission process


</blockquote>

### Certification

<blockquote class="quote">

#### Basics

1. Your bot must have a banner (either bot card and/or bot page)
2. Your bot should have a high quality bot page including a good long/short description and good banner choices
3. Your bot must be verified and in at least 100 servers at minimum. A recommendation that may result in a denial is the requirement of 500 servers but this is decided on a per-case basis. Hundred servers is minimum however
4. Your bot will be held up to higher standards than normal and also represents Fates List as a whole
5. Your bot must post stats to Fates List at least once per month or it will be uncertified. Vote webhooks for Fates List is recommended and this does affect certification however it is not a hard requirement
6. Your bot must have a consistent uptime and communicate with its users on maintenances and other downtime consistently
7. Your bot must have unique features or be the first to have said features. It must implement these features in a good high-quality way that conforms to users expectations
8. Your bot must meet our bot requirements as well as the certification requirements
9. Your bot may be exempted from requirements it does not meet on a case by case basis that staff (Admins/Mods+) will decide and/or vote on. We will let you know more information during the process
10. You may apply for certification on our support server by creating a support ticket with Certification as the selected option. Your bot will undergo some basic automated checks and will then be sent to us. We will DM you when we are retesting your bot and for any updates or other info we have. Having a closed DM/friend requests will result in denial!


</blockquote>

<blockquote class="quote">

#### Commands

1. At least 98% to 100% of all commands should work unless the bot does not *have* commands (chat bots etc)
2. All commands must implement error handling. Using embeds is recommended in commands
3. The majority of all commands should gave clear documentation on how to use it, preferably with examples


</blockquote>

<blockquote class="quote">

#### Perks

1. Certified Bots appear higher on the main page and will be above all bots other than the random bot
2. Special channel to show off certified bots and potential access to #general or a channel for just your bot!
3. Access to in-development 'unstable' API endpoints and potentially some certified bot only features
4. Little to no API ratelimits as you are trusted to use the API responsibly. This *will* get revoked and your bot *may* be banned if you abuse this (decided on a case by case basis)!
5. More coming soon ❤️


</blockquote>



This section was made to handle GDPR requirements such as data requests and deletions.

::: info

**This can only be done for your *own* user id for security purposes unless you are a Overseer (which is our version of a owner)**

:::

::: action-gdpr-request

### Request Data

<div class="form-group">
    <label for='user-id'>User ID</label>
    <input 
        class="form-control"
        name='user-id' 
        id='user-id'
        type="number"
        placeholder="User ID. See note above"
    />
    <button id="request-btn" onclick="dataRequest()">Request</button>
</div>

:::

<div id="request-data-area"></div>