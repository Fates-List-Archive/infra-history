::: warning

There are many types of webhooks in Fates List. Please choose the one you use carefully. Also note that all Fates List webhooks (excl. Discord Integration) will have a Authorization header with your API Token or Webhook Secret so you can validate the request. You will also see a X-Request-Sig header that is a HMAC SHA256 of the request body signed with your API Token or Webhook Secret for extra security.

:::

Vote Webhooks are the webhook type if you want to just capture votes in a simple format that is compatible with other lists. If you want more events like review creation and review voting, edit bot and other such events, you will need to switch to the websockets (see [Websockets](../../websockets/getting-started)) especially if you want real time stats.


Note that extra fields may be present

| Key | Description | Type |
| :--- | :--- | :--- |
| id | This is the ID of the user who voted for your bot | [Snowflake](../structures/basic-structures.md#terminology) |
| votes | This is how many votes your bot now has | Integer |
| test | This key is only returned if you are testing your webhook. It will always be true if sent. Use this to check for test webhook or not. | Boolean? |
| payload | This will always be ”event” in Vote Webhook. Ignore it. It’s a implementation detail that bots now rely on seeing for some reason. | String |
