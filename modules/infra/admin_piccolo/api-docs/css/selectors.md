**Key**

TYPE() means that there are many TYPEs as subchildren of this object and TYPE[] means that there are multiple of these TYPES retrieved as an array and not as subchildren when you use document.querySelectorAll on it. TYPE{} means both and is equivalent to TYPE()[]. Anything in bold is a variable and you should see the description for information about it.

**This may not be always accurate, use 'Inspect Element' when in doubt**

| Name | Description | Tag  | Type | Object | Selector |
| :--- | :--- | :--- | :--- | :--- | :--- |
| content | The entire div your bot page is in | div | id | Bot | #content |
| avatar | The bots avatar | img | id | Avatar | #avatar |
| username | The bots username | h3 | id | Username | #username |
| description | Your bots short description | h3 | id | Description | #description |
| buttons | The main buttons. If you want to change an individual button, .buttons-**button_name** | div | id | Button() | #buttons |
| buttons-**button_name** | A specific button, see the [Buttons](../buttons) section for more information on button names | button | id | Button | #buttons-**button_name** |
| key-container | The div containing tags and promotions both | div | id | KeyContainer | #key-container |
| tags | The div containing all your tags and the header | div | id | Tag() | #tags |
| tags-header | The "Tags" part of the tags | h5 | id | TagHeader | #tags-header |
| tags-container | The div inside #tags that contains just the tags (not the header) | div | id | TagInner() | #tags-container |
| tags-container-inner | The div inside #tags-container to help position the tags | div | id | Tag() | #tags-container-inner |
| tags-**tag_name**-button | The actual tag, see the [Tags](../tags) section for more information on tag names | button | id  | TagButton | #tags-**tag_name**-button |
| promo | This is the div containing all promotions | div | id | PromoFull | #promo |
| promo-header | This is the header of all the promotions (the Special Promotions/Events) | h5 | id  | PromoHeader | #promo-header |
| promo-container | This is the container for a promo | div[] | class | Promotion[] | .promo-container |
| promo-container-**index** | This is one promo based on jinja2 loop.index which is a number going from 0 to the N-1th promo index | div | id | Promotion | #promo-container-**index** |
| long-description | The bots long description. All links are given the long-desc-link class (selector: .long-desc-link) | div | id | LongDescription | #long-description |
| switcher | This is the bot switcher (The Description, Review, Commands, About and Admin tabs) | div | id | BotSwitcher | #switcher |
| tablinks | All of the tabs currently | button[] | class | Tab[] | .tablinks |
| **tab_name**-tab-button | The actual switcher tab, see the [Switcher Tabs](tabs.md) section for more information on the tab names  | button | id | Tab | #**tab_name**-tab-button |
| review_form | This is the review form used when making reviews. It is internal and is only being documented to be complete. Do not change this unless absolutely needed | form | id | _ReviewForm | #review_form |
| reviewreply-**review_id** | This is the review form used when making replies to reviews. It is internal and is only being documented to be complete. Do not change this unless absolutely needed. The review id here is the id of the review you are trying to reply to. | form | id | _ReviewReply | #reviewreply-**review_id** |
| review-**review_id** | This is the review form used when editing reviews. It is internal and is only being documented to be complete. Do not change this unless absolutely needed. The review id here is the id of the review you are trying to edit. | form | id | _ReviewEdit | #review-**review_id** |
| review-header | This is the review header (The place with stars and the edit link) | div[] | class | ReviewHeader[] | .review-header |
| review-user | This is the main review comtainer | div{} | class | ReviewUser{} | .review-user |
| reviews | The bot review container | div | id | BotReviews | #reviews |
| range-slider | The slider for the creatiom and editing of bot reviews and replies. | input[] | class | BotRangeSlider[] | .range-slider |
