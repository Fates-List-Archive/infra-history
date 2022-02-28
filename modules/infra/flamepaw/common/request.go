package common

import (
	"context"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"flamepaw/types"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/go-redis/redis/v8"

	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

var (
	mutex sync.Mutex
)

func GetWebhook(ctx context.Context, table_name string, id string, db *pgxpool.Pool) (ok bool, w_type int32, w_secret string, w_url string) {
	var webhookType pgtype.Int4
	var webhookURL pgtype.Text
	var apiToken pgtype.Text
	var webhookSecret pgtype.Text

	var field_name string = "bot_id"
	if table_name == "servers" {
		field_name = "guild_id"
	}

	err := db.QueryRow(ctx, "SELECT webhook_type, webhook, api_token, webhook_secret FROM "+table_name+" WHERE "+field_name+" = $1", id).Scan(&webhookType, &webhookURL, &apiToken, &webhookSecret)
	if err != nil {
		log.Error(err)
		return false, types.FatesWebhook, "", ""
	}

	if webhookType.Status != pgtype.Present {
		log.Warning("No webhook type is set")
		return false, types.FatesWebhook, "", ""
	}

	if webhookURL.Status != pgtype.Present {
		return false, types.FatesWebhook, "", ""
	}
	var secret string

	if webhookSecret.Status == pgtype.Present && strings.ReplaceAll(webhookSecret.String, " ", "") != "" {
		secret = webhookSecret.String
	} else if apiToken.Status == pgtype.Present {
		secret = apiToken.String
	} else {
		log.Warning("Neither webhook secret nor api token is defined")
		return false, types.FatesWebhook, "", ""
	}
	return true, webhookType.Int, secret, webhookURL.String
}

// Contains a webhook request
type request struct {
	eventId    string
	webhookURL string
	secret     string
	data       string
	userId     string
	botId      string
	tries      int
}

func channelWebhookReq(
	ctx context.Context,
	db *pgxpool.Pool,
	redis *redis.Client,
	data request,
) bool {
	mutex.Lock()
	defer mutex.Unlock()

	check := redis.Exists(ctx, "block-req:"+data.userId+":"+data.botId).Val()

	if check > 0 {
		log.Error("Request to " + data.userId + " locked with bot id of " + data.botId)
		return false
	}

	if data.tries > 5 {
		_, err := db.Exec(ctx, "UPDATE bot_api_event SET posted = $1 WHERE id = $2", types.WebhookPostError, data.eventId)
		if err != nil {
			log.Error(err)
			return false
		}
		return false
	}

	data.tries++

	// Create HMAC request signature
	mac := hmac.New(sha256.New, []byte(data.secret))
	mac.Write([]byte(data.data))
	exportedMAC := hex.EncodeToString(mac.Sum(nil))

	body := strings.NewReader(data.data)
	client := &http.Client{Timeout: 10 * time.Second}
	req, err := http.NewRequest("POST", data.webhookURL, body)

	if err != nil {
		log.Error(err)
		return channelWebhookReq(ctx, db, redis, data)
	}
	req.Header.Set("Authorization", data.secret)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "Dragon/0.1a0")
	req.Header.Set("X-Request-Sig", exportedMAC)

	if err != nil {
		log.Error(err)
		return channelWebhookReq(ctx, db, redis, data)
	}

	resp, err := client.Do(req)
	if err != nil {
		log.Error(err)
		return channelWebhookReq(ctx, db, redis, data)
	}

	log.WithFields(log.Fields{
		"status_code": resp.StatusCode,
	}).Debug("Got response")

	if resp.StatusCode >= 400 && resp.StatusCode != 401 {
		log.Error(err)
		return channelWebhookReq(ctx, db, redis, data)
	}

	redis.Set(ctx, "block-req:"+data.userId+":"+data.botId, "0", time.Hour*4)
	_, err = db.Exec(ctx, "UPDATE bot_api_event SET posted = $1 WHERE id = $2", types.WebhookPostSuccess, data.eventId)
	log.Error(err)
	return true
}

func WebhookReq(ctx context.Context, redis *redis.Client, db *pgxpool.Pool, eventId string, webhookURL string, secret string, data string, userId string, botId string, tries int) bool {
	reqData := request{
		eventId:    eventId,
		webhookURL: webhookURL,
		secret:     secret,
		data:       data,
		userId:     userId,
		botId:      botId,
		tries:      tries,
	}
	return channelWebhookReq(ctx, db, redis, reqData)
}

func errHandle(err error) {
	if err != nil {
		log.Error(err)
	}
}
