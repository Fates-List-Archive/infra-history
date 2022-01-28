// Based on https://github.com/gorilla/websocket/blob/master/examples/chat/main.go

// Copyright 2013 The Gorilla WebSocket Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

package webserver

import (
	"encoding/json"
	"flamepaw/common"
	"flamepaw/types"
	"fmt"
	"strconv"
	"strings"
	"time"

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

var logger = log.New()

func apiReturn(done bool, reason interface{}, context interface{}) gin.H {
	if reason == "EOF" {
		reason = "Request body required"
	}

	if reason == "" {
		reason = nil
	}

	if context == nil {
		return gin.H{
			"done":   done,
			"reason": reason,
		}
	} else {
		return gin.H{
			"done":   done,
			"reason": reason,
			"ctx":    context,
		}
	}
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

func StartWebserver(db *pgxpool.Pool, redis *redis.Client) {
	hub := newHub(db, redis)
	go hub.run()

	r := gin.New()

	r.Use(ginlogrus.Logger(logger), gin.Recovery())

	pprof.Register(r, "api/dragon/pprof")

	r.NoRoute(func(c *gin.Context) {
		c.JSON(404, apiReturn(false, "Not Found", nil))
	})
	router := r.Group("/api/dragon")

	router.GET("/__stats", func(c *gin.Context) {
		c.String(200, spew.Sdump(hub.clients))
	})

	router.POST("/github", func(c *gin.Context) {
		var gh types.GithubWebhook
		err := c.BindJSON(&gh)
		if err != nil {
			log.Error(err)
			c.JSON(400, apiReturn(false, err, nil))
			return
		}

		var header = c.Request.Header.Get("X-GitHub-Event")

		/*if gh.Repo.FullName != "" {
			c.JSON(200, apiReturn(true, "Not Flamepaw/Dragon", nil))
			return
		}*/

		var messageSend discordgo.MessageSend

		if header == "push" {
			var commitList string
			for _, commit := range gh.Commits {
				commitList += commit.Message + "(" + commit.ID + ")\n"
			}

			messageSend = discordgo.MessageSend{
				Embeds: []*discordgo.MessageEmbed{
					{
						Title:       "Push on:" + gh.Repo.FullName,
						Description: commitList,
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

		common.DiscordMain.ChannelMessageSendComplex("836337073618812928", &messageSend)

		c.JSON(200, apiReturn(true, nil, nil))
	})

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
			c.JSON(400, apiReturn(false, err.Error(), nil))
			return
		}

		vote.BotID = c.Param("id")

		if _, err := strconv.ParseInt(vote.BotID, 10, 64); err != nil {
			c.JSON(400, apiReturn(false, err.Error(), nil))
			return
		}

		var auth types.InternalUserAuth

		if err := c.ShouldBindHeader(&auth); err != nil {
			c.JSON(400, apiReturn(false, err.Error(), nil))
			return
		}

		var authcheck pgtype.Int8
		err := db.QueryRow(ctx, "SELECT user_id FROM users WHERE user_id = $1 AND api_token = $2", vote.UserID, auth.AuthToken).Scan(&authcheck)
		if err != nil && err != pgx.ErrNoRows {
			c.JSON(400, apiReturn(false, "Invalid User Token", nil))
			return
		}

		if authcheck.Status != pgtype.Present && !(common.Debug && vote.UserID == "0") {
			c.JSON(401, apiReturn(false, "You are not logged in. Please try logging in and out and then try again.", nil))
			return
		}

		log.WithFields(log.Fields{
			"user_id": vote.UserID,
			"bot_id":  vote.BotID,
			"test":    vote.Test,
		}).Info("User vote")

		key := "vote_lock:" + vote.UserID
		check := redis.PTTL(ctx, key).Val()

		var debug string
		if common.Debug {
			debug = "**DEBUG (for nerds)**\nRedis TTL: " + strconv.FormatInt(check.Milliseconds(), 10) + "\nKey: " + key + "\nTest: " + strconv.FormatBool(vote.Test)
		}

		if check.Milliseconds() == 0 || vote.Test {
			var votesDb pgtype.Int8
			var flags pgtype.Int4Array

			err := db.QueryRow(ctx, "SELECT flags, votes FROM bots WHERE bot_id = $1", vote.BotID).Scan(&flags, &votesDb)

			if err == pgx.ErrNoRows {
				c.JSON(400, apiReturn(false, "No bot found?", nil))
				return
			} else if err != nil {
				c.JSON(400, apiReturn(false, err.Error(), nil))
				return
			}

			for _, v := range flags.Elements {
				if int(v.Int) == types.BotFlagSystem.Int() {
					c.JSON(400, apiReturn(false, "You can't vote for system bots!", nil))
					return
				}
			}

			if !vote.Test {
				go addUserVote(db, redis, vote.UserID, vote.BotID)
			} else {
				vote.UserID = "519850436899897346"
			}

			votes := votesDb.Int + 1

			eventId := common.CreateUUID()

			voteEvent := map[string]interface{}{
				"votes": votes,
				"id":    vote.UserID,
				"ctx": map[string]interface{}{
					"user":  vote.UserID,
					"votes": votes,
					"test":  vote.Test,
				},
				"m": map[string]interface{}{
					"e":    types.EventBotVote,
					"user": vote.UserID,
					"t":    -1,
					"ts":   float64(time.Now().Unix()) + 0.001, // Make sure its a float by adding 0.001
					"eid":  eventId,
				},
			}

			vote_b, err := json.Marshal(voteEvent)
			if err != nil {
				log.Error(err)
				c.JSON(400, apiReturn(false, "Could not create vote webhook... Please contact us on our support server for more information: "+err.Error(), nil))
				return
			}

			voteStr := string(vote_b)

			go common.AddWsEvent(ctx, redis, "bot-"+vote.BotID, eventId, voteEvent)

			go func() {
				ok, webhookType, secret, webhookURL := common.GetWebhook(ctx, "bots", vote.BotID, db)

				if ok {
					if webhookType == types.DiscordWebhook {
						go common.SendIntegration(common.DiscordMain, vote.UserID, vote.BotID, webhookURL, int(votes))
					} else {
						go common.WebhookReq(ctx, db, eventId, webhookURL, secret, voteStr, 0)
					}
					log.Debug("Got webhook type of " + strconv.Itoa(int(webhookType)))
				}

				if !vote.Test {
					redis.Set(ctx, key, 0, 8*time.Hour)
				}
			}()

			c.JSON(200, apiReturn(true, "You have successfully voted for this bot :)", nil))
		} else {
			hours := check / time.Hour
			mins := (check - (hours * time.Hour)) / time.Minute
			secs := (check - (hours*time.Hour + mins*time.Minute)) / time.Second
			c.JSON(429, apiReturn(false, fmt.Sprintf("Please wait %02d hours, %02d minutes %02d seconds before trying to vote for bots", hours, mins, secs), debug))
		}
	})

	router.GET("/ws", func(c *gin.Context) {
		serveWs(hub, c.Writer, c.Request)
	})

	err := r.RunUnix("/home/meow/fatesws.sock")
	if err != nil {
		log.Fatal("could not start listening: ", err)
		return
	}

}
