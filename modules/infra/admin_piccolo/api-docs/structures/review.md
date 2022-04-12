All reviews share the below format. This structure is used in the Get Review API and in new review and edit review events.

Reviews totally have two parts. The list of review objects \(and their replies\) in the reviews key and a key called average\_stars at the end of all reviews and replies which tells you the average stars your bot \(or server\) has overall as a float

| Key | Description | Type |
| :--- | :--- | :--- |
| reviews | The list of review objects (and their replies) | [Review](review.md)[] |
| stats | A stats object | Structure |

#### Review Object

| Key | Description | Type |
| :--- | :--- | :--- |
| id  | This is the id of the review | UUID |
| parent_id | The reviews parent ID (the review this review is a reply to) if the review is a reply. If the review is not a reply, this will be ``null``. Use this to check if a review is a reply or not. | UUID? |
| user\_id | The User ID of the person who made the review | Snowflake |
| star\_rating | How many stars \(out of 10\) was given | Float (serialized as String) |
| votes | A review votes object giving the votes of this review | Review Votes object (see below) |
| review_text | The content/text of the review | String |
| flagged | Whether the review has been flagged or not. You won’t get an event when this happens for safety reasons | Boolean |
| epoch | The epoch timestamps of all the times the review was edited | Snowflake\[\] |
| user | The user \(BaseUser object\) who performed the event on the review \(see [Basic Structures](basic-structures.md)\) | BaseUser \(see [Basic Structures](basic-structures.md#structures)\) |
| user_review | If ``user_id`` is specified in query, this will contain the [Review](review.md) that the user has made for this bot, otherwise ``nul``. This is internally used by sunbeam to show user review at the very top. | [Review](review.md)? |
| replies | The list of review objects which are replies to your bot | [Review](review.md)\[\] |

#### Review Votes Object

| Key | Description | Type |
| :--- | :--- | :--- |
| upvotes | The User IDs of all people who have upvoted the review | Snowflake\[\] |
| downvotes | The User IDs of all people who have downvoted the review | Snowflake\[\] |
