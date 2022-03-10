This page was made to handle GDPR requirements such as data requests and deletions. **It is not the terms of service of Lynx. Lynx follows the [Fates List Terms Of Service](https://fateslist.xyz/frostpaw/tos)**

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