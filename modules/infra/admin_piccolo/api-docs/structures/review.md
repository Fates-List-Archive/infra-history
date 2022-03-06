All reviews share the below format. This structure is used in the Get Review API and in new review and edit review events.

Reviews totally have two parts. The list of review objects \(and their replies\) in the reviews key and a key called average\_stars at the end of all reviews and replies which tells you the average stars your bot \(or server\) has overall as a float

| Key | Description | Type |
| :--- | :--- | :--- |
| reviews | The list of review objects (and their replies) | [Review](review.md)[] |
| average\_stars | The average stars your bot or guild has overall with all reviews \(not replies\) taken into account | Float |

#### Review Object

| Key | Description | Type |
| :--- | :--- | :--- |
| id  | This is the id of the review | UUID |
| reply | Whether the review is a reply or not | Boolean |
| user\_id | The User ID of the person who made the review | Snowflake |
| star\_rating | How many stars \(out of 10\) was given | Float |
| review | The content/text of the review | String |
| review\_upvotes | The User IDs of all people who have upvoted the review | Snowflake\[\] |
| review\_downvotes | The User IDs of all people who have downvoted the review | Snowflake\[\] |
| flagged | Whether the review has been flagged or not. You won’t get an event when this happens for safety reasons | Boolean |
| epoch | The epoch timestamps of all the times the review was edited | Snowflake\[\] |
| time\_past | The amount of time since the review was first created | Snowflake |
| user | The user \(BaseUser object\) who performed the event on the review \(see [Basic Structures](basic-structures.md)\) | BaseUser \(see [Basic Structures](basic-structures.md#structures)\) |
| replies | The list of review objects which are replies to your bot | [Review](review.md)\[\] |
