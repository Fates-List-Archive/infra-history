# Flamepaw
Flamepaw is internally used by the bot to provide a RESTful API for tasks requiring high concurrency. The base url is ``https://api.fateslist.xyz/flamepaw``

## Pprof

#### PPROF /pprof
**Description:** Golang pprof (debugging, may not always exist!)

**Request Body:**
```json
null
```

**Response Body:**
```json
null
```

## Ping Server

#### GET /ping
**Description:** Ping the server

**Request Body:**
```json
null
```

**Response Body:**
```json
{
	"done": false,
	"reason": null,
	"context": null
}
```

## Get Stats

#### GET /__stats
**Description:** Get stats of websocket server

**Request Body:**
```json
null
```

**Response Body:**
```json
null
```

## Github Webhook

#### POST /github
**Description:** Post to github webhook. Needs authorization

**Request Body:**
```json
{
	"ref": "",
	"action": "",
	"Commits": null,
	"repository": {
		"id": 0,
		"name": "",
		"full_name": "",
		"description": "",
		"url": "",
		"owner": {
			"login": "",
			"id": 0,
			"avatar_url": "",
			"url": "",
			"html_url": "",
			"organizations_url": ""
		},
		"html_url": "",
		"commits_url": ""
	},
	"pusher": {
		"name": "",
		"description": ""
	},
	"sender": {
		"login": "",
		"id": 0,
		"avatar_url": "",
		"url": "",
		"html_url": "",
		"organizations_url": ""
	},
	"head_commit": {
		"id": "",
		"message": "",
		"author": {
			"name": "",
			"email": "",
			"username": ""
		}
	},
	"pull_request": {
		"id": 0,
		"number": 0,
		"state": "",
		"locked": false,
		"title": "",
		"body": "",
		"html_url": "",
		"url": "",
		"user": {
			"login": "",
			"id": 0,
			"avatar_url": "",
			"url": "",
			"html_url": "",
			"organizations_url": ""
		},
		"base": {
			"repo": {
				"id": 0,
				"name": "",
				"full_name": "",
				"description": "",
				"url": "",
				"owner": {
					"login": "",
					"id": 0,
					"avatar_url": "",
					"url": "",
					"html_url": "",
					"organizations_url": ""
				},
				"html_url": "",
				"commits_url": ""
			},
			"id": 0,
			"number": 0,
			"state": "",
			"title": "",
			"body": "",
			"html_url": "",
			"url": "",
			"ref": "",
			"label": "",
			"user": {
				"login": "",
				"id": 0,
				"avatar_url": "",
				"url": "",
				"html_url": "",
				"organizations_url": ""
			},
			"commits_url": ""
		},
		"head": {
			"repo": {
				"id": 0,
				"name": "",
				"full_name": "",
				"description": "",
				"url": "",
				"owner": {
					"login": "",
					"id": 0,
					"avatar_url": "",
					"url": "",
					"html_url": "",
					"organizations_url": ""
				},
				"html_url": "",
				"commits_url": ""
			},
			"id": 0,
			"number": 0,
			"state": "",
			"title": "",
			"body": "",
			"html_url": "",
			"url": "",
			"ref": "",
			"label": "",
			"user": {
				"login": "",
				"id": 0,
				"avatar_url": "",
				"url": "",
				"html_url": "",
				"organizations_url": ""
			},
			"commits_url": ""
		}
	},
	"issue": {
		"id": 0,
		"number": 0,
		"state": "",
		"title": "",
		"body": "",
		"html_url": "",
		"url": "",
		"user": {
			"login": "",
			"id": 0,
			"avatar_url": "",
			"url": "",
			"html_url": "",
			"organizations_url": ""
		}
	}
}
```

**Response Body:**
```json
{
	"done": false,
	"reason": null,
	"context": null
}
```

## Websocket

#### WS /ws
**Description:** The websocket gateway for Fates List

**Request Body:**
```json
null
```

**Response Body:**
```json
null
```


