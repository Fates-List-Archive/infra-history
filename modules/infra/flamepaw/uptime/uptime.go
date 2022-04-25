package uptime

import (
	"context"
	"flamepaw/common"
	"flamepaw/types"
	"time"

	"github.com/bwmarrin/discordgo"
	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

var (
	UptimeRunning  bool
	UptimeFirstRun bool
	ErrBots        []string = []string{} // List of bots that actually don't exist on main server
	ErrBotOffline  []string = []string{} // List of bots that are offline
)

func UptimeFunc(ctx context.Context, db *pgxpool.Pool, discord *discordgo.Session, t time.Time) {
	if !UptimeFirstRun {
		UptimeFirstRun = true
		log.Info("Uptime subsystem now up at time: ", time.Now())
		return
	}
	UptimeRunning = true
	log.Info("Called uptime function at time: ", t)
	bots, err := db.Query(ctx, "SELECT bot_id::text FROM bots WHERE state = $1 OR state = $2", types.BotStateApproved.Int(), types.BotStateCertified.Int())
	if err != nil {
		log.Error(err)
		return
	}
	defer bots.Close()
	i := 0
	ErrBots = []string{}
	ErrBotOffline = []string{}
	for bots.Next() {
		var botId pgtype.Text
		bots.Scan(&botId)
		if botId.Status != pgtype.Present {
			log.Error("Bot ID is not present during uptime checks...: ", i)
			continue
		}
		status, err := discord.State.Presence(common.MainServer, botId.String)
		if err != nil {
			_, err := discord.State.Member(common.MainServer, botId.String)
			if err != nil {
				// Bot doesn't actually exist!
				ErrBots = append(ErrBots, botId.String)
				continue
			}
		}
		if status == nil || status.Status == discordgo.StatusOffline {
			log.Warning(botId.String, " is offline right now!")
			_, err := db.Exec(ctx, "UPDATE bots SET uptime_checks_failed = uptime_checks_failed + 1, uptime_checks_total = uptime_checks_total + 1 WHERE bot_id = $1", botId.String)
			if err != nil {
				log.Error(err)
			}
			ErrBotOffline = append(ErrBotOffline, botId.String)
			continue
		}
		_, err = db.Exec(ctx, "UPDATE bots SET uptime_checks_total = uptime_checks_total + 1 WHERE bot_id = $1", botId.String)
		if err != nil {
			log.Error(err)
		}
		i += 1
	}
	log.Info("Finished uptime checks at time: ", time.Now(), ".\nBots Not Found: ", len(ErrBots))
	UptimeRunning = false
}
