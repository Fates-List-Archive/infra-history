package squirrelflight

import (
	"context"
	"flamepaw/common"
	"strings"
	"time"

	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

// This must be run as a goroutine
func StartVR(ctx context.Context, db *pgxpool.Pool, rdb *redis.Client) {
	for range time.Tick(time.Second * 5) {
		log.Info("Called vote reminders")
		reminders, err := db.Query(ctx, "SELECT user_id::text, vote_reminders::text[], vote_reminder_channel::text FROM users WHERE vote_reminders != '{}'")
		if err != nil {
			panic(err)
		}

		for reminders.Next() {
			var userID pgtype.Text
			var voteReminders pgtype.TextArray
			var voteReminderChannel pgtype.Text
			var canVote []string
			err := reminders.Scan(&userID, &voteReminders, &voteReminderChannel)
			if err != nil {
				log.Error(err)
			}

			if voteReminderChannel.String == "" {
				voteReminderChannel.String = common.VoteReminderChannel
			}

			// Vote locks are global, so if we can vote for one bot, we can vote for all of them
			check := rdb.TTL(ctx, "vote_lock:"+userID.String).Val()
			acked := rdb.TTL(ctx, "votereminder_ack:"+userID.String).Val()
			if check > 0 {
				continue
			}
			if acked > 0 {
				continue
			}
			rdb.Set(ctx, "votereminder_ack:"+userID.String, "0", time.Hour*6)
			for _, v := range voteReminders.Elements {
				canVote = append(canVote, "<@"+v.String+"> ("+v.String+")")
			}
			log.WithFields(log.Fields{
				"userID":              userID.String,
				"voteReminders":       canVote,
				"voteReminderChannel": voteReminderChannel.String,
				"acked":               acked,
				"check":               check,
			}).Info("Vote Reminder Info")
			msg := "Hey <@" + userID.String + ">, you can vote for " + strings.Join(canVote, ", ") + " or did you forget?"
			_, err = common.DiscordSquirrelflight.ChannelMessageSend(voteReminderChannel.String, msg)
			if err != nil {
				log.Error(err)
			}
		}
		reminders.Close()
	}
}
