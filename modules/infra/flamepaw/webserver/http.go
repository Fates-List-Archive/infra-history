// Based on https://github.com/gorilla/websocket/blob/master/examples/chat/main.go

// Copyright 2013 The Gorilla WebSocket Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

package webserver

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"crypto/sha512"
	"crypto/subtle"
	"encoding/hex"
	"flamepaw/common"
	"flamepaw/types"
	"fmt"
	"io/ioutil"
	"strconv"
	"strings"
	"time"

	docencoder "encoding/json"

	jsoniter "github.com/json-iterator/go"

	"github.com/Fates-List/discordgo"
	"github.com/davecgh/go-spew/spew"
	"github.com/gin-contrib/pprof"
	"github.com/gin-gonic/gin"
	ginlogrus "github.com/toorop/gin-logrus"

	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

var json = jsoniter.ConfigCompatibleWithStandardLibrary

var logger = log.New()

var Docs string = "# Flamepaw\nFlamepaw is internally used by the bot to provide a RESTful API for tasks requiring high concurrency.\n\n"

// Given name and docs,
func document(method, route, name, docs string, reqBody interface{}, resBody interface{}) {
	Docs += "## " + strings.Title(strings.ReplaceAll(name, "_", " ")) + "\n\n"
	Docs += "#### " + strings.ToUpper(method) + " " + route + "\n"
	Docs += "**Description:** " + docs + "\n\n"
	var body, err = docencoder.MarshalIndent(resBody, "", "\t")
	if err != nil {
		body = []byte("No documentation available")
	}
	var ibody, err2 = docencoder.MarshalIndent(reqBody, "", "\t")
	if err2 != nil {
		body = []byte("No documentation available")
	}
	Docs += "**Request Body:**\n```json\n" + string(ibody) + "\n```\n\n"
	Docs += "**Response Body:**\n```json\n" + string(body) + "\n```\n\n"
}

// API return
func apiReturn(c *gin.Context, statusCode int, done bool, reason interface{}, context interface{}) {
	if reason == "EOF" {
		reason = "Request body required"
	}

	if reason == "" {
		reason = nil
	}

	var ret = gin.H{"done": done, "reason": reason}
	if context != nil {
		ret["ctx"] = context
	}
	c.Header("Content-Type", "application/json")
	body, err := json.MarshalToString(ret)
	if err != nil {
		body, _ = json.MarshalToString(gin.H{"done": false, "reason": "Internal server error: " + err.Error()})
		statusCode = 500
	}
	c.String(statusCode, body)
}

func addUserVote(db *pgxpool.Pool, redis *redis.Client, userID string, botID string) {
	// Create a user vote
	_, err := db.Exec(ctx, "UPDATE bots SET votes = votes + 1, total_votes = total_votes + 1 WHERE bot_id = $1", botID)
	if err != nil {
		log.Error(err)
	}

	var ts pgtype.Int8

	err = db.QueryRow(ctx, "SELECT COUNT(1) FROM bot_voters WHERE user_id = $1 AND bot_id = $2", userID, botID).Scan(&ts)

	if err != nil {
		log.Error(err)
	}

	if ts.Status != pgtype.Present {
		_, err = db.Exec(ctx, "INSERT INTO bot_voters (user_id, bot_id) VALUES ($1, $2)", userID, botID)
		if err != nil {
			log.Error(err)
		}
	} else {
		_, err = db.Exec(ctx, "UPDATE bot_voters SET timestamps = array_append(timestamps, NOW()) WHERE bot_id = $1 AND user_id = $2", botID, userID)
		if err != nil {
			log.Error(err)
		}
	}
}

func VoteBot(db *pgxpool.Pool, redis *redis.Client, userID string, botID string, test bool) (bool, string) {
	key := "vote_lock:" + userID
	check := redis.PTTL(ctx, key).Val()

	var debug string
	debug = "**DEBUG (for nerds)**\nRedis TTL: " + strconv.FormatInt(check.Milliseconds(), 10) + "\nKey: " + key + "\nTest: " + strconv.FormatBool(test)

	if check.Milliseconds() == 0 || test {
		var votesDb pgtype.Int8
		var flags pgtype.Int4Array

		err := db.QueryRow(ctx, "SELECT flags, votes FROM bots WHERE bot_id = $1", botID).Scan(&flags, &votesDb)

		if err == pgx.ErrNoRows {
			return false, "No bot found?"
		} else if err != nil {
			return false, err.Error()
		}

		for _, v := range flags.Elements {
			if int(v.Int) == types.BotFlagSystem.Int() {
				return false, "You can't vote for system bots!"
			}
		}

		realID := userID

		if !test {
			go addUserVote(db, redis, userID, botID)
		} else {
			userID = "519850436899897346"
		}

		votes := votesDb.Int + 1

		eventId := common.CreateUUID()

		voteEvent := map[string]any{
			"votes": votes,
			"id":    userID,
			"ctx": map[string]any{
				"user":  userID,
				"rid":   realID,
				"tvn":   "In a test vote, user will be set to Mewbot's bot id, rid always contains real id, but always validate test vs non-test first",
				"dn":    "https://docs.fateslist.xyz",
				"votes": votes,
				"test":  test,
			},
			"m": map[string]any{
				"e":    types.EventBotVote,
				"user": userID,
				"t":    -1,
				"ts":   float64(time.Now().Unix()) + 0.001, // Make sure its a float by adding 0.001
				"eid":  eventId,
			},
		}

		vote_b, err := json.Marshal(voteEvent)
		if err != nil {
			log.Error(err)
			return false, "Could not create vote webhook... Please contact us on our support server for more information: " + err.Error()
		}

		voteStr := string(vote_b)

		go func() {
			common.AddWsEvent(ctx, redis, "bot-"+botID, eventId, voteEvent)

			ok, webhookType, secret, webhookURL := common.GetWebhook(ctx, "bots", botID, db)

			if ok {
				if webhookType == types.DiscordWebhook {
					common.SendIntegration(common.DiscordMain, userID, botID, webhookURL, int(votes))
				} else {
					common.WebhookReq(ctx, db, eventId, webhookURL, secret, voteStr, 0)
				}
				log.Debug("Got webhook type of " + strconv.Itoa(int(webhookType)))
			}

			if !test {
				redis.Set(ctx, key, 0, 8*time.Hour)
			}
		}()

		return true, "You have successfully voted for this bot :).\n\nPro Tip: You can vote for bots directly on your server using Squirrelflight, join our support server for more information but Squirreflight also supports vote reminders as well!"
	} else {
		hours := check / time.Hour
		mins := (check - (hours * time.Hour)) / time.Minute
		secs := (check - (hours*time.Hour + mins*time.Minute)) / time.Second
		return false, fmt.Sprintf("Please wait %02d hours, %02d minutes %02d seconds before trying to vote for bots\n\n%s", hours, mins, secs, debug)
	}
}

func StartWebserver(db *pgxpool.Pool, redis *redis.Client) {
	hub := newHub(db, redis)
	go hub.run()

	r := gin.New()

	r.Use(ginlogrus.Logger(logger), gin.Recovery())

	document("PPROF", "/api/dragon/pprof", "pprof", "Golang pprof (debugging, may not always exist!)", nil, nil)
	pprof.Register(r, "api/dragon/pprof")

	r.NoRoute(func(c *gin.Context) {
		apiReturn(c, 404, false, "Not Found", nil)
	})
	router := r.Group("/api/dragon")

	document("GET", "/api/dragon/ping", "ping_server", "Ping the server", nil, types.APIResponse{})
	router.GET("/ping", func(c *gin.Context) {
		apiReturn(c, 200, true, nil, nil)
	})

	document("GET", "/api/dragon/__stats", "get_stats", "Get stats of websocket server", nil, nil)
	router.GET("/__stats", func(c *gin.Context) {
		stats := "Websocket server stats:\n\n"
		i := 0
		for client := range hub.clients {
			stats += fmt.Sprintf(
				"Client #%d\nID: %d\nIdentityStatus: %t\nBot: %t\nRLChannel: %s\nSendAll: %t\nSendNone: %t\nMessagePumpUp: %t\nToken: [redacted] \n\n\n",
				i,
				client.ID,
				client.IdentityStatus,
				client.Bot,
				client.RLChannel,
				client.SendAll,
				client.SendNone,
				client.MessagePumpUp,
			)
			i++
		}
		c.String(200, stats)
	})

	document("POST", "/api/dragon/github", "github_webhook", "Post to github webhook. Needs authorization", types.GithubWebhook{}, types.APIResponse{})
	router.POST("/github", func(c *gin.Context) {
		var bodyBytes []byte
		if c.Request.Body != nil {
			bodyBytes, _ = ioutil.ReadAll(c.Request.Body)
		}

		// Restore the io.ReadCloser to its original state
		c.Request.Body = ioutil.NopCloser(bytes.NewBuffer(bodyBytes))

		var signature = c.Request.Header.Get("X-Hub-Signature-256")

		mac := hmac.New(sha256.New, []byte(common.GHWebhookSecret))
		mac.Write([]byte(bodyBytes))
		expected := hex.EncodeToString(mac.Sum(nil))

		if "sha256="+expected != signature {
			log.Error(expected + " " + signature + " ")
			apiReturn(c, 401, false, "Invalid signature", nil)
			return
		}

		var gh types.GithubWebhook
		err := c.BindJSON(&gh)
		if err != nil {
			log.Error(err)
			apiReturn(c, 422, false, err.Error(), nil)
			return
		}

		var header = c.Request.Header.Get("X-GitHub-Event")

		var messageSend discordgo.MessageSend

		if header == "push" {
			var commitList string
			for _, commit := range gh.Commits {
				commitList += fmt.Sprintf("%s [%s](%s) | [%s](%s)\n", commit.Message, commit.ID[:7], commit.URL, commit.Author.Username, "https://github.com/"+commit.Author.Username)
			}

			messageSend = discordgo.MessageSend{
				Embeds: []*discordgo.MessageEmbed{
					{
						Color: 0x00ff1a,
						URL:   gh.Repo.URL,
						Author: &discordgo.MessageEmbedAuthor{
							Name:    gh.Sender.Login,
							IconURL: gh.Sender.AvatarURL,
						},
						Title: "Push on " + gh.Repo.FullName,
						Fields: []*discordgo.MessageEmbedField{
							{
								Name:  "Branch",
								Value: "**Ref:** " + gh.Ref + "\n" + "**Base Ref:** " + gh.BaseRef,
							},
							{
								Name:  "Commits",
								Value: commitList,
							},
							{
								Name:  "Pusher",
								Value: fmt.Sprintf("[%s](%s)", gh.Pusher.Name, "https://github.com/"+gh.Pusher.Name),
							},
						},
					},
				},
			}
		} else if header == "star" {
			var color int
			var title string
			if gh.Action == "created" {
				color = 0x00ff1a
				title = "Starred: " + gh.Repo.FullName
			} else {
				color = 0xff0000
				title = "Unstarred: " + gh.Repo.FullName
			}
			messageSend = discordgo.MessageSend{
				Embeds: []*discordgo.MessageEmbed{
					{
						Color: color,
						URL:   gh.Repo.URL,
						Title: title,
						Fields: []*discordgo.MessageEmbedField{
							{
								Name:  "User",
								Value: "[" + gh.Sender.Login + "]" + "(" + gh.Sender.HTMLURL + ")",
							},
						},
					},
				},
			}
		} else if header == "issues" {
			var body string = gh.Issue.Body
			if len(gh.Issue.Body) > 1000 {
				body = gh.Issue.Body[:1000]
			}

			if body == "" {
				body = "No description available"
			}

			var color int
			if gh.Action == "deleted" || gh.Action == "unpinned" {
				color = 0xff0000
			} else {
				color = 0x00ff1a
			}

			messageSend = discordgo.MessageSend{
				Embeds: []*discordgo.MessageEmbed{
					{
						Color: color,
						URL:   gh.Issue.HTMLURL,
						Author: &discordgo.MessageEmbedAuthor{
							Name:    gh.Sender.Login,
							IconURL: gh.Sender.AvatarURL,
						},
						Title: fmt.Sprintf("Issue %s on %s (#%d)", gh.Action, gh.Repo.FullName, gh.Issue.Number),
						Fields: []*discordgo.MessageEmbedField{
							{
								Name:  "Action",
								Value: gh.Action,
							},
							{
								Name:  "User",
								Value: fmt.Sprintf("[%s](%s)", gh.Sender.Login, gh.Sender.HTMLURL),
							},
							{
								Name:  "Title",
								Value: gh.Issue.Title,
							},
							{
								Name:  "Body",
								Value: body,
							},
						},
					},
				},
			}
		} else if header == "pull_request" {
			var body string = gh.PullRequest.Body
			if len(gh.PullRequest.Body) > 1000 {
				body = gh.PullRequest.Body[:1000]
			}

			if body == "" {
				body = "No description available"
			}

			var color int
			if gh.Action == "closed" {
				color = 0xff0000
			} else {
				color = 0x00ff1a
			}

			messageSend = discordgo.MessageSend{
				Embeds: []*discordgo.MessageEmbed{
					{
						Color: color,
						URL:   gh.PullRequest.HTMLURL,
						Author: &discordgo.MessageEmbedAuthor{
							Name:    gh.Sender.Login,
							IconURL: gh.Sender.AvatarURL,
						},
						Title: fmt.Sprintf("Pull Request %s on %s (#%d)", gh.Action, gh.Repo.FullName, gh.PullRequest.Number),
						Fields: []*discordgo.MessageEmbedField{
							{
								Name:  "Action",
								Value: gh.Action,
							},
							{
								Name:  "User",
								Value: fmt.Sprintf("[%s](%s)", gh.Sender.Login, gh.Sender.HTMLURL),
							},
							{
								Name:  "Title",
								Value: gh.PullRequest.Title,
							},
							{
								Name:  "Body",
								Value: body,
							},
							{
								Name:  "More Information",
								Value: fmt.Sprintf("**Base Ref:** %s\n**Base Label:** %s\n**Head Ref:** %s\n**Head Label:** %s", gh.PullRequest.Base.Ref, gh.PullRequest.Base.Label, gh.PullRequest.Head.Ref, gh.PullRequest.Head.Label),
							},
						},
					},
				},
			}
		} else if header == "issue_comment" {
			var body string = gh.Issue.Body
			if len(gh.Issue.Body) > 1000 {
				body = gh.Issue.Body[:1000]
			}

			if body == "" {
				body = "No description available"
			}

			var color int
			if gh.Action == "deleted" {
				color = 0xff0000
			} else {
				color = 0x00ff1a
			}

			messageSend = discordgo.MessageSend{
				Embeds: []*discordgo.MessageEmbed{
					{
						Color: color,
						URL:   gh.Issue.HTMLURL,
						Author: &discordgo.MessageEmbedAuthor{
							Name:    gh.Sender.Login,
							IconURL: gh.Sender.AvatarURL,
						},
						Title: fmt.Sprintf("Comment on %s (#%d) %s", gh.Repo.FullName, gh.Issue.Number, gh.Action),
						Fields: []*discordgo.MessageEmbedField{
							{
								Name:  "User",
								Value: fmt.Sprintf("[%s](%s)", gh.Sender.Login, gh.Sender.HTMLURL),
							},
							{
								Name:  "Title",
								Value: gh.Issue.Title,
							},
							{
								Name:  "Body",
								Value: body,
							},
						},
					},
				},
			}
		} else if header == "pull_request_review_comment" {
			var body string = gh.PullRequest.Body
			if len(gh.PullRequest.Body) > 1000 {
				body = gh.PullRequest.Body[:1000]
			}

			if body == "" {
				body = "No description available"
			}

			var color int
			if gh.Action == "deleted" {
				color = 0xff0000
			} else {
				color = 0x00ff1a
			}

			messageSend = discordgo.MessageSend{
				Embeds: []*discordgo.MessageEmbed{
					{
						Color: color,
						URL:   gh.PullRequest.HTMLURL,
						Author: &discordgo.MessageEmbedAuthor{
							Name:    gh.Sender.Login,
							IconURL: gh.Sender.AvatarURL,
						},
						Title: "Pull Request Review Comment on " + gh.Repo.FullName + " (#" + strconv.Itoa(gh.PullRequest.Number) + ")",
						Fields: []*discordgo.MessageEmbedField{
							{
								Name:  "User",
								Value: fmt.Sprintf("[%s](%s)", gh.Sender.Login, gh.Sender.HTMLURL),
							},
							{
								Name:  "Title",
								Value: gh.PullRequest.Title,
							},
							{
								Name:  "Body",
								Value: body,
							},
						},
					},
				},
			}
		} else {
			messageSend = discordgo.MessageSend{
				Content: "**Action: " + header + "**",
				TTS:     false,
				File: &discordgo.File{
					Name:        "gh-event.txt",
					ContentType: "application/octet-stream",
					Reader:      strings.NewReader(spew.Sdump(gh)),
				},
			}
		}

		_, err = common.DiscordMain.ChannelMessageSendComplex(common.GithubChannel, &messageSend)

		if err != nil {
			log.Error(err)
			apiReturn(c, 400, false, "Error sending message: "+err.Error(), nil)
			return
		}

		apiReturn(c, 200, true, nil, nil)
	})

	document("GET", "/api/dragon/users/:uid/bots/:bid/ts/:ts/_vote-token", "get_vote_token", "Returns a vote token. Needs whitelisting and a access key.", nil, types.APIResponse{})
	router.GET("/users/:uid/bots/:bid/ts/:ts/_vote-token", func(c *gin.Context) {
		var auth types.InternalUserAuth

		if err := c.ShouldBindHeader(&auth); err != nil {
			apiReturn(c, 401, false, "Invalid User Token: "+err.Error(), nil)
			return
		}

		var userID = c.Param("uid")
		var botID = c.Param("bid")
		var ts = c.Param("ts")

		tsInt, err := strconv.Atoi(ts)

		if err != nil {
			apiReturn(c, 400, false, "Invalid timestamp: "+err.Error(), nil)
			return
		}

		if time.Now().Unix()-int64(tsInt) > 10 {
			apiReturn(c, 400, false, "Timestamp is too old", nil)
			return
		}

		mac := hmac.New(sha512.New, common.VoteTokenAccessKeyBytes)
		mac.Write([]byte(userID + "/" + botID + "/" + ts + "/Shadowsight"))
		expected := hex.EncodeToString(mac.Sum(nil))

		if subtle.ConstantTimeCompare([]byte(auth.AuthToken), []byte(expected)) != 1 {
			apiReturn(c, 401, false, "Invalid Access Key", nil)
			return
		}

		voteToken := common.RandString(512)
		redis.Set(ctx, "vote_token:"+voteToken, userID+botID, 30*time.Second)
		apiReturn(c, 200, true, nil, voteToken)
	})

	document("OPTIONS", "/api/dragon/bots/:id/votes", "vote_bot", "Creates a vote for a bot. Needs authorization. This is the CORS code", nil, nil)
	router.OPTIONS("/bots/:id/votes", func(c *gin.Context) {
		var origin string = c.GetHeader("Origin")
		var ref string = c.GetHeader("Referer")
		if ref == "https://sunbeam.fateslist.xyz" || ref == "https://sunbeam-cf.fateslist.xyz" {
			origin = ref
		}
		if origin == "" {
			origin = "fateslist.xyz"
		}
		c.Header("Access-Control-Allow-Origin", origin)
		c.Header("Access-Control-Allow-Headers", "Frostpaw, Authorization, Content-Type")
		c.Header("Access-Control-Allow-Methods", "PATCH, OPTIONS")
		c.Header("Access-Control-Allow-Credentials", "true")
	})

	document("PATCH", "/api/dragon/bots/:id/votes", "vote_bot", "Creates a vote for a bot. Needs authorization. This is the actual route", types.UserVote{}, types.APIResponse{})
	router.PATCH("/bots/:id/votes", func(c *gin.Context) {
		var origin string = c.GetHeader("Origin")
		if origin == "" {
			origin = "fateslist.xyz"
		}
		c.Header("Access-Control-Allow-Origin", origin)
		c.Header("Access-Control-Allow-Headers", "Frostpaw, Authorization, Content-Type")
		c.Header("Access-Control-Allow-Methods", "PATCH")
		c.Header("Access-Control-Allow-Credentials", "true")

		var vote types.UserVote
		if err := c.ShouldBindJSON(&vote); err != nil {
			apiReturn(c, 422, false, err.Error(), nil)
			return
		}

		vote.BotID = c.Param("id")

		if _, err := strconv.ParseInt(vote.BotID, 10, 64); err != nil {
			apiReturn(c, 422, false, err.Error(), nil)
			return
		}

		var auth types.InternalUserAuth

		if err := c.ShouldBindHeader(&auth); err != nil {
			apiReturn(c, 401, false, "Invalid User Token: "+err.Error(), nil)
			return
		}

		if strings.HasPrefix(auth.AuthToken, "Vote ") {
			check := redis.Get(ctx, "vote_token:"+strings.Replace(auth.AuthToken, "Vote ", "", 1)).Val()
			if check != (vote.UserID + vote.BotID) {
				apiReturn(c, 401, false, "Invalid Vote Token", nil)
				return
			}
			redis.Del(ctx, "vote_token:"+auth.AuthToken)
		} else {
			var authcheck pgtype.Int8
			err := db.QueryRow(ctx, "SELECT user_id FROM users WHERE user_id = $1 AND api_token = $2", vote.UserID, auth.AuthToken).Scan(&authcheck)
			if err != nil && err != pgx.ErrNoRows {
				apiReturn(c, 401, false, "Invalid User Token", nil)
				return
			}

			if authcheck.Status != pgtype.Present && !(common.Debug && vote.UserID == "0") {
				apiReturn(c, 401, false, "You are not logged in. Please try logging in and out and then try again.", nil)
				return
			}
		}

		log.WithFields(log.Fields{
			"user_id": vote.UserID,
			"bot_id":  vote.BotID,
			"test":    vote.Test,
		}).Info("User vote")

		ok, res := VoteBot(db, redis, vote.UserID, vote.BotID, vote.Test)
		if ok {
			apiReturn(c, 200, true, res, nil)
		} else {
			apiReturn(c, 400, false, res, nil)
		}
	})

	document("WS", "/api/dragon/ws", "websocket", "The websocket gateway for Fates List", nil, nil)
	router.GET("/ws", func(c *gin.Context) {
		serveWs(hub, c.Writer, c.Request)
	})

	err := r.RunUnix("/home/meow/fatesws.sock")
	if err != nil {
		log.Fatal("could not start listening: ", err)
		return
	}
}
