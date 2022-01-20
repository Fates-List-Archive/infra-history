// Based on https://github.com/gorilla/websocket/blob/master/examples/chat/client.go

// Copyright 2013 The Gorilla WebSocket Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

package webserver

import (
	"context"
	"encoding/json"
	"flamepaw/types"
	"net/http"
	"strconv"
	"time"

	"github.com/jackc/pgtype"
	log "github.com/sirupsen/logrus"

	"github.com/gorilla/websocket"
)

const (
	// Time allowed to write a message to the peer.
	writeWait = 10 * time.Second

	// Time allowed to read the next pong message from the peer.
	pongWait = 60 * time.Second

	// Send pings to peer with this period. Must be less than pongWait.
	pingPeriod = (pongWait * 9) / 10

	// Maximum message size allowed from peer.
	maxMessageSize = 4096

	// Maximum requests allowed
	maxRequests = 20

	// Ratelimit duration
	ratelimitDuration = 7 * time.Minute
)

var (
	sepChar = []byte{31}
	ctx     = context.Background()
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  2048,
	WriteBufferSize: 2048,
}

// Client is a middleman between the websocket connection and the hub.
type Client struct {
	hub *Hub

	// The websocket connection.
	conn *websocket.Conn

	// Buffered channel of outbound messages.
	send chan []byte

	// Channel for control messages (identity, invalid_conn etc)
	control chan []byte

	// ID of the client
	ID int

	// API Token of the client
	Token string

	// Bot is true, guild is false
	Bot bool

	// Identity status of the client (true = identified, false = not yet identified)
	IdentityStatus bool

	// Message pump up
	MessagePumpUp bool

	// Send prior
	SendAll bool

	// Send event status
	SendNone bool

	// RL Channel
	RLChannel string
}

// readPump pumps messages from the websocket connection to the hub.
//
// The application runs readPump in a per-connection goroutine. The application
// ensures that there is at most one reader on a connection by executing all
// reads from this goroutine.
func (c *Client) readPump() {
	defer func() {
		c.hub.unregister <- c
		closeWs(c, types.InternalError)
	}()
	c.conn.SetReadLimit(maxMessageSize)
	c.conn.SetReadDeadline(time.Now().Add(pongWait))
	c.conn.SetPongHandler(func(string) error { c.conn.SetReadDeadline(time.Now().Add(pongWait)); return nil })
	for {
		_, message, err := c.conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				log.Error("Websocket closed: ", err)
			}
			closeWs(c, types.InvalidConn)
			return
		}

		if !c.IdentityStatus {
			var payload types.WebsocketIdentifyPayload
			err := json.Unmarshal(message, &payload)
			if err != nil {
				log.Error("Websocket unmarshal error: ", err)
				sendWsData(c, "invalid_payload", err.Error())
				closeWs(c, types.InvalidAuth)
				return
			}

			// pId is the bot id in payload
			pId, err := strconv.Atoi(payload.ID)

			if err != nil {
				log.Error("Websocket unmarshal error: ", err)
				sendWsData(c, "invalid_payload", err.Error())
				closeWs(c, types.InvalidAuth)
				return
			}
			if pId <= 0 || payload.Token == "" {
				sendWsData(c, "invalid_payload", "Invalid ID or token sent. Got ID of "+payload.ID+" and api token of "+payload.Token)
				closeWs(c, types.InvalidAuth)
				return
			}

			var tgtID pgtype.Int8

			var sql string
			var mod string
			if payload.Bot {
				sql = "SELECT bot_id FROM bots WHERE bot_id = $1 AND api_token = $2"
				mod = "bot"
			} else {
				sql = "SELECT guild_id FROM servers WHERE guild_id = $1 AND api_token = $2"
				mod = "server"
			}

			err = c.hub.postgres.QueryRow(ctx, sql, payload.ID, payload.Token).Scan(&tgtID)
			if err != nil {
				log.Error("Websocket identify error: ", err)
				sendWsData(c, "invalid_auth", err.Error())
				closeWs(c, types.InvalidAuth)
				return
			}
			if tgtID.Status != pgtype.Present {
				sendWsData(c, "invalid_auth", "No bot/guild found/Invalid auth")
				closeWs(c, types.InvalidAuth)
				return
			}
			c.ID = pId
			c.Token = payload.Token
			c.Bot = payload.Bot
			c.IdentityStatus = true
			c.SendAll = payload.SendAll
			c.SendNone = payload.SendNone
			c.RLChannel = "wsrl-" + strconv.Itoa(c.ID) + "-" + mod
			// Identify successful. Ratelimits can be handled here later

			// Request ratelimit check (IDENTITY = 2 requests)
			var rlCurrentInt int = 0
			var rlCurrent string = "0"
			rlCurrent = c.hub.redis.Get(ctx, c.RLChannel).Val()
			if rlCurrent == "" {
				c.hub.redis.Set(ctx, c.RLChannel, "2", ratelimitDuration)
			} else {
				rlCurrentInt, err := strconv.Atoi(rlCurrent)
				if err != nil {
					c.hub.redis.Set(ctx, c.RLChannel, "2", ratelimitDuration)
					rlCurrentInt = 2
				}
				c.hub.redis.IncrBy(ctx, c.RLChannel, 2)
				rlCurrent = strconv.Itoa(rlCurrentInt)
			}

			// Ensure rlCurrentInt is properly set (this is likely due to some scoping issue)
			rlCurrentInt, _ = strconv.Atoi(rlCurrent)
			rlCurrentInt += 2
			rlCurrent = strconv.Itoa(rlCurrentInt)

			if rlCurrentInt > maxRequests {
				sendWsData(c, "ratelimited", "Past max requests that can be sent ("+rlCurrent+")")
				closeWs(c, types.Ratelimited)
				return
			}

			// End of ratelimit code should be here
			sendWsData(c, "ready", "Waiting for messages with "+rlCurrent+" already made")
			go msgPump(c)
		} else {
			// Ratelimit it
			r := c.hub.redis.Incr(ctx, c.RLChannel).Val()
			if r > maxRequests {
				sendWsData(c, "ratelimited", "Past max requests that can be sent ("+strconv.Itoa(int(r))+")")
				closeWs(c, types.Ratelimited)
				return
			}
		}
	}
}

// Pumps events to the write pump. Central event pumper
func msgPump(c *Client) {
	if !c.IdentityStatus {
		return
	}
	if !c.MessagePumpUp {
		c.MessagePumpUp = true
	}

	var mod string
	if c.Bot {
		mod = "bot-"
	} else {
		mod = "server-"
	}

	channelName := mod + strconv.Itoa(c.ID)
	globalChan := "global"

	go func() {
		if !c.SendAll {
			return
		}
		msgs := c.hub.redis.HGet(ctx, channelName, "ws").Val()
		if msgs != "" {
			sendMessages(c, []byte(msgs), channelName)
		}
		msgs = c.hub.redis.Get(ctx, globalChan).Val()
		if msgs != "" {
			sendMessages(c, []byte(msgs), globalChan)
		}
		time.Sleep(1 * time.Second)
		go sendWsData(c, "done_prior", "Done sending all prior messages")
	}()

	if !c.SendNone {
		pubsub := c.hub.redis.Subscribe(ctx, channelName, globalChan)
		defer pubsub.Close()
		ch := pubsub.Channel()
		for msg := range ch {
			if !c.IdentityStatus || !c.MessagePumpUp {
				return
			}

			go sendMessages(c, []byte(msg.Payload), msg.Channel)
		}
	}
}

// Goroutine to send messages
func sendMessages(c *Client, payload []byte, channel string) {
	defer recovery()
	var event map[string]interface{}
	json.Unmarshal(payload, &event)
	for _, v := range event {
		event, err := json.Marshal(map[string]interface{}{
			"code":    "event",
			"control": false,
			"detail":  nil,
			"dat":     v,       // Data
			"chan":    channel, // Channel
		})
		if err != nil {
			log.Warn("Error in msg pump: ", err)
			continue
		}

		if !c.IdentityStatus || !c.MessagePumpUp {
			return
		}
		c.send <- event
	}
}

// writePump pumps messages from the hub to the websocket connection.
//
// A goroutine running writePump is started for each connection. The
// application ensures that there is at most one writer to a connection by
// executing all writes from this goroutine.
func (c *Client) writePump() {
	ticker := time.NewTicker(pingPeriod)
	defer func() {
		ticker.Stop()
		c.hub.unregister <- c
		closeWs(c, types.InternalError)
	}()
	for {
		select {
		case message, ok := <-c.send:
			c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if !ok {
				// The hub closed the channel.
				closeWs(c, types.InvalidConn)
				return
			}

			w, err := c.conn.NextWriter(websocket.TextMessage)
			if err != nil {
				return
			}
			w.Write(message)
			w.Write(sepChar)

			// Add queued chat messages to the current websocket message.
			n := len(c.send)
			for i := 0; i < n; i++ {
				w.Write(sepChar)
				w.Write(<-c.send)
				w.Write(sepChar)
			}

			if err := w.Close(); err != nil {
				return
			}
		case message, ok := <-c.control:
			c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if !ok {
				// The hub closed the channel.
				closeWs(c, types.InvalidConn)
				return
			}

			w, err := c.conn.NextWriter(websocket.TextMessage)
			if err != nil {
				return
			}

			w.Write(message)

			time.Sleep(1 * time.Millisecond)

			if err := w.Close(); err != nil {
				return
			}

		case <-ticker.C:
			c.conn.SetWriteDeadline(time.Now().Add(writeWait))
			if err := c.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
			// Then send an OP code of ping
			sendWsData(c, "ping", "")
		}
	}
}

func getRatelimit(c *Client) int {
	var requestsMade int
	if c.ID != 0 {
		requests, err := strconv.Atoi(c.hub.redis.Get(ctx, c.RLChannel).Val())
		if err == nil {
			requestsMade = requests
		}
	} else {
		requestsMade = maxRequests + 1 // So requests remaining is always -1
	}
	return requestsMade
}

func sendWsData(c *Client, code string, e string) error {
	defer recovery()
	payload, err := json.Marshal(types.WebsocketPayload{
		Code:              code,
		Detail:            e,
		Timestamp:         float64(time.Now().Unix()),
		RequestsRemaining: maxRequests - getRatelimit(c),
		Control:           true,
	})
	if err != nil {
		return err
	}

	c.control <- payload
	return nil
}

func closeWs(c *Client, code types.WebsocketCloseCode) {
	time.Sleep(1 * time.Millisecond)
	c.MessagePumpUp = false
	c.conn.WriteControl(websocket.CloseMessage, websocket.FormatCloseMessage(code.Code, code.Description), time.Now().Add(2*time.Second))
	c.conn.Close()
}

// serveWs handles websocket requests from the peer.
func serveWs(hub *Hub, w http.ResponseWriter, r *http.Request) {
	defer recovery()

	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Warn(err)
		return
	}
	client := &Client{hub: hub, conn: conn, send: make(chan []byte, 256), control: make(chan []byte, 256), IdentityStatus: false, MessagePumpUp: false}
	client.hub.register <- client

	go client.writePump()

	err = sendWsData(client, "identity", "Send Bot ID and API Token as id and token keys in json format. Set send_all to true if you want all events to be sent during startup but this may cause disconnects, more memory usage, more ratelimits and instability. Set send_none to true to not send any events at all after sending prior ones if send_all is set to true. Set bot to true for bot and false for server")

	if err != nil {
		log.Warn(err)
		client.hub.unregister <- client
		return
	}

	go client.readPump()

	// Allow collection of memory referenced by the caller by doing all work in
	// new goroutines.
}

func recovery() {
	error := recover()
	if error != nil {
		log.Error(error)
	}
}
