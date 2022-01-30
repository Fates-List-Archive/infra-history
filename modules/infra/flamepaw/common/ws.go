package common

import (
	"context"

	jsoniter "github.com/json-iterator/go"

	"github.com/go-redis/redis/v8"
	log "github.com/sirupsen/logrus"
)

var json = jsoniter.ConfigCompatibleWithStandardLibrary

func AddWsEvent(ctx context.Context, redis *redis.Client, channel string, eventId string, event map[string]interface{}) {
	wsEvent, err := json.Marshal(map[string]map[string]interface{}{
		eventId: event,
	})
	if err != nil {
		log.Error(err)
		return
	}
	redis.Publish(ctx, channel, wsEvent)
	botEvents := redis.HGet(ctx, channel, "ws").Val()
	if botEvents == "" {
		botEvents = "{}"
	}
	var botEventsNew map[string]interface{}
	err = json.Unmarshal([]byte(botEvents), &botEventsNew)
	if err != nil {
		log.Error(err)
		return
	}
	botEventsNew[eventId] = event
	botEventsB, err := json.Marshal(botEventsNew)
	if err != nil {
		log.Error(err)
		return
	}
	redis.HSet(ctx, channel, "ws", string(botEventsB))
}
