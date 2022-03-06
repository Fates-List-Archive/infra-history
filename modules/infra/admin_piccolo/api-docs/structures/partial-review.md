This page covers the structure of a partial review which is seen in review events

Partial reviews are sent on new review and edit review events. They are a partial representation of the created or edited review:

| Key | Description | Type |
| :--- | :--- | :--- |
| user | The user ([BaseUser](basic-structures.md#baseuser) object) who performed the event on the review \(see [Basic Structures](basic-structures.md)\) | [BaseUser](basic-structures.md#baseuser) |
| id | This is the id of the review | UUID |
| star\_rating | How many stars \(out of 10\) was given | Float |
| reply | Whether the review is a reply or not. | Boolean |
| root | The parent of the review. This will be null if the review is not a reply. Only sent in a new\_review event. | UUID? |
| review | The content/text of the review | String |
| upvotes | The amount of upvotes the review has. Only sent in vote\_review event. | Integer? |
| downvotes | The amount of downvotes the review has. Only sent in vote\_review event. | Integer? |

