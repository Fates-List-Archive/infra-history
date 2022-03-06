package admin

import (
	"context"
	"flamepaw/common"
	"flamepaw/slashbot"
	"flamepaw/supportsystem"
	"flamepaw/types"
	"strconv"
	"time"

	"github.com/Fates-List/discordgo"
	"github.com/davecgh/go-spew/spew"
	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

const embedColorGood = 0x00ff00
const embedColorBad = 0xe74c3c
const perMessageQueueCount = 4 // 4 bots per message

var (
	commands         = make(map[string]AdminOp)
	commandNameCache = make(map[string]string)
	staffOnlyFlags   = []types.BotFlag{types.BotFlagStatsLocked, types.BotFlagVoteLocked, types.BotFlagSystem, types.BotFlagStaffLocked}
)

func autocompleter(state int) func(context types.SlashContext) (ac []*discordgo.ApplicationCommandOptionChoice) {
	return func(context types.SlashContext) (ac []*discordgo.ApplicationCommandOptionChoice) {
		dataVal := slashbot.GetArg(common.DiscordMain, context.Interaction, "bot", false)
		data, ok := dataVal.(string)
		if !ok {
			return
		}

		bots, err := context.Postgres.Query(context.Context, "SELECT bot_id::text, username_cached, verifier FROM bots WHERE state = $1 AND (bot_id::text ILIKE $2 OR username_cached ILIKE $2) ORDER BY created_at DESC LIMIT 25", state, "%"+data+"%")
		if err != nil {
			log.Error(err)
			return
		}
		defer bots.Close()

		for bots.Next() {
			var botId pgtype.Text
			var usernameCached pgtype.Text
			var verifier pgtype.Int8
			bots.Scan(&botId, &usernameCached, &verifier)

			var username string = usernameCached.String
			if username == "" {
				user, err := common.DiscordMain.User(botId.String)
				if err != nil {
					username = botId.String
				} else {
					_, err = context.Postgres.Exec(context.Context, "UPDATE bots SET username_cached = $1 WHERE bot_id = $2", user.Username, botId.String)
					if err != nil {
						log.Error(err)
					}
					username = user.Username
				}
			}

			var val discordgo.ApplicationCommandOptionChoice = discordgo.ApplicationCommandOptionChoice{
				Name:  username,
				Value: botId.String,
			}

			if verifier.Status == pgtype.Present && verifier.Int > 0 {
				if state == types.BotStateUnderReview.Int() {
					val.Name += " (Claimed by " + strconv.FormatInt(verifier.Int, 10) + ")"
				} else if state == types.BotStateDenied.Int() {
					val.Name += " (Denied by " + strconv.FormatInt(verifier.Int, 10) + ")"
				}
			}

			ac = append(ac, &val)
		}

		return
	}
}

func UpdateBotLogs(ctx context.Context, postgres *pgxpool.Pool, userId string, botId string, action types.UserBotAuditLog) {
	_, err := postgres.Exec(ctx, "INSERT INTO user_bot_logs (user_id, bot_id, action) VALUES ($1, $2, $3)", userId, botId, action)
	if err != nil {
		log.Error(err)
	}
}

// Admin OP Getter
func CmdInit() map[string]types.SlashCommand {
	// Mock is only here for registration, actual code is on slashbot

	commands["USERSTATE"] = AdminOp{
		InternalName: "userstate",
		Cooldown:     types.CooldownBan,
		Description:  "Sets a users state",
		SlashRaw:     true,
		Event:        types.EventNone,
		MinimumPerm:  5,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionInteger,
				Name:        "state",
				Description: "The new state to set",
				Choices:     types.GetStateChoices(types.UserStateUnknown),
				Required:    true,
			},
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "user",
				Description: "The user id to set the state of",
				Required:    true,
			},
		},
		Server: common.StaffServer,
		Handler: func(context types.SlashContext) string {
			stateVal := slashbot.GetArg(common.DiscordMain, context.Interaction, "state", false)
			state, ok := stateVal.(int64)
			if !ok {
				return "Invalid state"
			}
			userVal := slashbot.GetArg(common.DiscordMain, context.Interaction, "user", false)
			user, ok := userVal.(string)
			if !ok {
				return "Invalid user provided"
			}
			_, err := context.Postgres.Exec(context.Context, "UPDATE users SET state = $1 WHERE user_id = $2", state, user)
			if err != nil {
				return err.Error()
			}
			return "OK."
		},
	}

	commands["MOCK"] = AdminOp{
		InternalName: "mock",
		Cooldown:     types.CooldownNone,
		Description:  "Mocks a guild in server listing",
		SlashRaw:     true,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "guild",
				Description: "Guild to mock",
			},
		},
		Server: common.StaffServer,
	}

	// Reset all bot votes
	commands["RESETVOTESALL"] = AdminOp{
		InternalName: "resetallvotes",
		Cooldown:     types.CooldownNone,
		Description:  "Reset votes for all bots on the list",
		MinimumPerm:  6,
		Event:        types.EventNone,
		SlashRaw:     true,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "reason",
				Description: "Reason for resetting all votes. Defaults to Monthly Vote Reset",
				Required:    false,
			},
		},
		Server: common.StaffServer,
		Handler: func(context types.SlashContext) string {
			if context.Reason == "" {
				context.Reason = "Monthly Votes Reset"
			}
			bots, err := context.Postgres.Query(context.Context, "SELECT bot_id, votes FROM bots")
			if err != nil {
				log.Error(err)
				return err.Error()
			}

			defer bots.Close()

			tx, err := context.Postgres.Begin(context.Context)
			if err != nil {
				return err.Error()
			}

			defer tx.Rollback(context.Context)

			for bots.Next() {
				var botId pgtype.Int8
				var votes pgtype.Int8
				bots.Scan(&botId, &votes)
				if botId.Status != pgtype.Present {
					return "Unable to get botID and votes"
				}
				tx.Exec(context.Context, "INSERT INTO bot_stats_votes_pm (bot_id, epoch, votes) VALUES ($1, $2, $3)", botId.Int, float64(time.Now().Unix())+0.001, votes.Int)
				tx.Exec(context.Context, "UPDATE bots SET votes = 0 WHERE bot_id = $1", botId.Int)
			}
			err = tx.Commit(context.Context)
			if err != nil {
				return err.Error()
			}

			keys := context.Redis.Keys(context.Context, "vote_lock:*").Val()

			context.Redis.Del(context.Context, keys...)

			embed := discordgo.MessageEmbed{
				URL:         "https://fateslist.xyz",
				Title:       "All Bot Votes Reset",
				Description: "All bots have had its votes reset!",
				Color:       embedColorGood,
				Fields: []*discordgo.MessageEmbedField{
					{
						Name:  "Reason",
						Value: context.Reason,
					},
				},
			}
			common.DiscordMain.ChannelMessageSendComplex(common.SiteLogs, &discordgo.MessageSend{
				Embed: &embed,
			})
			return "OK. But make sure to clear the database to get rid of existing vote locks"
		},
	}

	commands["SENDROLEMSG"] = AdminOp{
		InternalName: "sendrolemsg",
		Cooldown:     types.CooldownNone,
		Description:  "Send role message",
		MinimumPerm:  5,
		Event:        types.EventNone,
		Server:       common.StaffServer,
		SlashRaw:     true,
		Handler: func(context types.SlashContext) string {
			supportsystem.SendRolesMessage(common.DiscordMain, true)
			return "Done"
		},
	}

	// Load command name cache to map internal name to the command
	for cmdName, v := range commands {
		commandNameCache[v.InternalName] = cmdName
	}
	return slashIr()
}

func GetCommandSpew() string {
	return spew.Sdump("Admin commands loaded: ", commands)
}
