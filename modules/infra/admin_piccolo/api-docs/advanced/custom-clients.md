Custom clients are supported however you are responsible for keeping them up-to-date. Some features require whitelisting in order to use (DM a Fates List staff member for this):

## Frostpaw Auth

::: warning

This feature requires whitelisting in order to use

**Whitelist form**

If you wish to request for a whitelist, fill out the following form:

<div class="form-group">
    <label for='whitelist-reason'>Reason</label>
    <textarea 
        class="form-control"
        name='whitelist-reason' 
        id='whitelist-reason'
        placeholder="Why do you feel like you should be whitelisted"
    ></textarea>
    <label for='privacy-policy'>Privacy Policy</label>
    <textarea 
        class="form-control"
        name='privacy-policy' 
        id='privacy-policy'
        placeholder="What do you (plan to) do with user information. Be specific"
    ></textarea>
    <label for='whitelist'>Client Information</label>
    <textarea 
        class="form-control"
        name='client-info' 
        id='client-info'
        placeholder="What user agent will your client use. What platform will it be for. Who will be responsible for damages caused and who will be maintaining the client."
    ></textarea>
    <button onclick="genClientWhitelist()">Request</button>
</div>

:::

In order to authorize to the API through OAuth (without using a inputted user token, you need to use Frostpaw Authentication)

### Getting the login link

The first step in Frostpaw Auth is getting the login link:

To do this:

- Store the current location if needed (use localStorage if needed)

- Send a GET request to `https://api.fateslist.xyz/oauth`.
    - Make sure to send the `Frostpaw` header (set this to the client version in the [About](https://fateslist.xyz/frostpaw/about) section)
    - Set the `Frostpaw-Server` header to the *origin servers hostname*, for example https://fateslist.xyz/bot/admin/add would set `Frostpaw-Server` as https://fateslist.xyz. You can use `window.location.origin` for this if this is for a browser
    - The final redirect *requires explicit whitelisting, possible source code access and a possible POC to be shown*

- The final url to redirect to will be in the `url` key of the response

- We will guide you on the `redirect_uri` side. There is a very specific route you will need to give (official sunbeam client uses `/frostpaw/login` and as such your client will also need to expose a `/frostpaw/login` route as well)

### Get login information

This step is domain-dependent, you might need another server to set the required cookies and/or parse JWTs. We do not recommend using `/jwtparse/_sunbeam` or our `Set-Cookie` headers without asking us beforehand as these may or may not work in the future and may need extra whitelisting in the future

The general idea is the below:

- Get the code and state from query string (`new URLSearchParams(window.location.search)` if you are on browser)

- Send a POST request to `https://api.fateslist.xyz/oauth`
    - Make sure to send the `Frostpaw` header (set this to the client version in the [About](https://fateslist.xyz/frostpaw/about) section)
    - Set the `Frostpaw-Server` header to the *origin servers hostname*, for example https://fateslist.xyz/bot/admin/add would set `Frostpaw-Server` as https://fateslist.xyz. You can use `window.location.origin` for this if this is for a browser
    - Be sure to set `code` to the code you got from query string
    - Handle errors from our API properly (ask staff if you need a test account banned etc.). This is where `done` is set to `false`
    - If all goes well, you will get a json with `done` set to `true`. In this case, you will get a `token` and a `user` amongst other things (this changes constantly, see [here](https://api.fateslist.xyz/api/docs/redoc#operation/login_user) for up to date information) ([BaseUser](../structures/basic-structures.md#baseuser)). Store these somehow and redirect back to where they last were (you did store this in step 1 right?)

- [Relevant API Docs](https://api.fateslist.xyz/api/docs/redoc#operation/login_user)

### Bot/Server Pages

Nothing special, just set ``Frostpaw`` header when sending these

## Bot/Server Invites

Nothing special, just set ``Frostpaw-Invite`` header when sending these

## Documentation

All endpoints for v3 are documented on the [endpoints](../endpoints) page,

## Headers

Make sure to send the `Frostpaw` header on *all requests* (set this to the client version in the [About](https://fateslist.xyz/frostpaw/about) section). Our anti-abuse code takes this header into account and your responses may be easier to parse as well with possibly fewer restrictions in some areas.