package common

import (
	"context"
	"dragon/types"
	"net/http"
	"strings"

	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

func GetWebhook(ctx context.Context, table_name string, id string, db *pgxpool.Pool) (ok bool, w_type int32, w_secret string, w_url string) {
	var webhookType pgtype.Int4
	var webhookURL pgtype.Text
	var apiToken pgtype.Text
	var webhookSecret pgtype.Text
	err := db.QueryRow(ctx, "SELECT webhook_type, webhook, api_token, webhook_secret FROM "+table_name+" WHERE bot_id = $1", id).Scan(&webhookType, &webhookURL, &apiToken, &webhookSecret)
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

func WebhookReq(ctx context.Context, db *pgxpool.Pool, eventId string, webhookURL string, secret string, data string, tries int) bool {
	if tries > 5 {
		_, err := db.Exec(ctx, "UPDATE bot_api_event SET posted = $1 WHERE id = $2", types.WebhookPostError, eventId)
		if err != nil {
			log.Error(err)
			return false
		}
		return false
	}
	body := strings.NewReader(data)
	client := &http.Client{}
	req, err := http.NewRequest("POST", webhookURL, body)
	if err != nil {
		return WebhookReq(ctx, db, eventId, webhookURL, secret, data, tries+1)
	}
	req.Header.Set("Authorization", secret)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "Dragon/0.1a0")
	errHandle(err)
	if err != nil {
		return WebhookReq(ctx, db, eventId, webhookURL, secret, data, tries+1)
	}
	resp, err := client.Do(req)
	errHandle(err)
	if err != nil {
		return WebhookReq(ctx, db, eventId, webhookURL, secret, data, tries+1)
	}
	log.WithFields(log.Fields{
		"status_code": resp.StatusCode,
	}).Debug("Got response")
	if resp.StatusCode >= 400 && resp.StatusCode != 401 {
		return WebhookReq(ctx, db, eventId, webhookURL, secret, data, tries+1)
	}
	_, err = db.Exec(ctx, "UPDATE bot_api_event SET posted = $1 WHERE id = $2", types.WebhookPostSuccess, eventId)
	errHandle(err)
	return true
}

func errHandle(err error) {
	if err != nil {
		log.Error(err)
	}
}
