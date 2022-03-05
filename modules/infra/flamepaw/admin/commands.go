package admin

import (
	"context"
	"errors"
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

	commands["MEASUREAPI"] = AdminOp{
		InternalName: "apim",
		Cooldown:     types.CooldownNone,
		Description:  "Measure API response times",
		Event:        types.EventNone,
		MinimumPerm:  4,
		SlashRaw:     true,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "user",
				Description: "The user to give coins to",
				Required:    true,
			},
		},
		Handler: func(context types.SlashContext) string {
			userVal := slashbot.GetArg(common.DiscordMain, context.Interaction, "user", false)
			user, ok := userVal.(string)
			if !ok {
				return "Invalid user"
			}
			currTimeJAPI := time.Now().Unix()
			japiJson, err, t := common.FetchUserRNG(user)
			if err == nil {
				err = errors.New("No errors")
			}
			timeJAPI := time.Now().Unix() - currTimeJAPI
			slashbot.SendIResponse(common.DiscordMain, context.Interaction, "JAPI JSON:\n"+spew.Sdump(japiJson)+"\n**Errors** "+err.Error()+"\n**Time taken** "+strconv.FormatInt(timeJAPI, 10)+"\n**Type** "+t, false)
			return "nop"
		},
	}

	commands["GIVECOINS"] = AdminOp{
		InternalName: "givecoins",
		Cooldown:     types.CooldownNone,
		Description:  "Give coins to a user",
		Event:        types.EventNone,
		MinimumPerm:  4,
		SlashRaw:     true,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionUser,
				Name:        "user",
				Description: "The user to give coins to",
				Required:    true,
			},
			{
				Type:        discordgo.ApplicationCommandOptionInteger,
				Name:        "coins",
				Description: "The amount of coins to give",
				Required:    true,
			},
		},
		Handler: func(context types.SlashContext) string {
			return "Work in progress"
		},
	}

	commands["SETFLAG"] = AdminOp{
		InternalName: "setflag",
		Cooldown:     types.CooldownNone,
		Description:  "Locks or unlocks a bot",
		Event:        types.EventNone,
		Server:       common.TestServer,
		MinimumPerm:  1,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionInteger,
				Name:        "flag",
				Description: "The flag to set",
				Choices:     types.GetStateChoices(types.BotFlagUnknown),
				Required:    true,
			},
		},
		Handler: func(context types.SlashContext) string {
			flagVal := slashbot.GetArg(common.DiscordMain, context.Interaction, "flag", false)
			flagRaw, ok := flagVal.(int64)
			if !ok {
				return "Invalid flag"
			}
			flag := types.GetBotFlag(int(flagRaw))
			if flag == types.BotFlagUnknown {
				return "Invalid flag"
			}

			if context.StaffPerm < 3 {
				for v := range staffOnlyFlags {
					if v == flag.Int() {
						return flag.ValStr() + " can only be set by permlevel 3 and higher!"
					}
				}
			}

			var currFlags pgtype.Int4Array

			err := context.Postgres.QueryRow(context.Context, "SELECT flags FROM bots WHERE bot_id = $1", context.Bot.ID).Scan(&currFlags)

			if err != nil {
				return err.Error()
			}

			var flagSet = make(map[int]bool)
			var removedFlag bool

			for _, currFlag := range currFlags.Elements {
				if flag.Int() == int(currFlag.Int) {
					removedFlag = true
					continue
				}
				flagSet[int(currFlag.Int)] = true
			}

			if !removedFlag {
				flagSet[flag.Int()] = true
			}

			var flagFinal []int

			for k := range flagSet {
				flagFinal = append(flagFinal, int(k))
			}

			_, err = context.Postgres.Exec(context.Context, "UPDATE bots SET flags = $1 WHERE bot_id = $2", flagFinal, context.Bot.ID)

			if err != nil {
				return err.Error()
			}

			return ""
		},
	}

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

	commands["PANICCHECK"] = AdminOp{
		InternalName: "paniccheck",
		Cooldown:     types.CooldownNone,
		Description:  "Test golang panics",
		MinimumPerm:  5,
		Event:        types.EventNone,
		SlashRaw:     true,
		SlashOptions: []*discordgo.ApplicationCommandOption{},
		Server:       common.StaffServer,
		Handler: func(context types.SlashContext) string {
			panic("Test panic")
		},
	}

	commands["LYNXRESET"] = AdminOp{
		InternalName: "lynxreset",
		Cooldown:     types.CooldownBan,
		Description:  "Reset Lynx Creds",
		MinimumPerm:  2,
		Event:        types.EventNone,
		Server:       common.StaffServer,
		SlashRaw:     true,
		Handler: func(context types.SlashContext) string {
			context.Postgres.Exec(context.Context, "UPDATE users SET api_token = $1, staff_verify_code = NULL WHERE user_id = $2", common.RandString(101), context.User.ID)
			return "Go to https://lynx.fateslist.xyz to get new credentials"
		},
	}

	// Adds a staff to our team!
	commands["ADDSTAFF"] = AdminOp{
		InternalName: "addstaff",
		Cooldown:     types.CooldownBan,
		Description:  "Adds a staff member to Fates List. This is the only supported way to add staff",
		MinimumPerm:  5,
		SlashRaw:     true,
		Event:        types.EventNone,
		Server:       common.StaffServer,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionUser,
				Name:        "user",
				Description: "The user to add to the Fates List Staff Team",
				Required:    true,
			},
		},
		Handler: func(context types.SlashContext) string {
			userVal := slashbot.GetArg(common.DiscordMain, context.Interaction, "user", false)
			user, ok := userVal.(*discordgo.User)
			if !ok {
				return "This user could not be found..."
			} else if user.Bot {
				return "You can't add bots to the staff team!"
			}

			// Check if the user in question is in the main server
			if _, err := common.DiscordMain.State.Member(common.MainServer, user.ID); err != nil {
				return "This user could not be found on the main server!"
			}

			commStaff, ok := common.StaffRoles["community_staff"]
			if !ok {
				return "Staff roles are not setup correctly! (community_staff)"
			}
			botReviewer, ok := common.StaffRoles["bot_reviewer"]
			if !ok {
				return "Staff roles are not setup correctly! (bot_reviewer)"
			}

			err := common.DiscordMain.GuildMemberRoleAdd(common.MainServer, user.ID, commStaff.ID)
			if err != nil {
				return "Failed to give community staff role. Do I have perms? Is the role ID correct?"
			}

			err = common.DiscordMain.GuildMemberRoleAdd(common.MainServer, user.ID, botReviewer.ID)
			if err != nil {
				return "Failed to give bot reviewer role. Do I have perms? Is the role ID correct?"
			}

			userDm, err := common.DiscordMain.UserChannelCreate(user.ID)

			_, err2 := common.DiscordMain.ChannelMessageSendComplex(userDm.ID, &discordgo.MessageSend{
				Content: "**You have been accepted onto our staff team!**\n" +
					"In order to begin testing bots and be a part of the Fates List Staff Team, you must join the below servers:\n\n" +
					"**Staff server:** <https://fateslist.xyz/server/" + common.StaffServer + "/invite>\n" +
					"**Testing server:** <https://fateslist.xyz/server/" + common.TestServer + "/invite>\n\n" +
					"After joining the staff server, you must run /getaccess to get your roles.\n" +
					"Finally, type /queue on our testing server to start testing bots. Feel free to ask any staff for help if you need it!",
			})

			if err != nil || err2 != nil {
				log.Error(err, err2)
				return "Could not DM this user! Please tell them to go to <https://fateslist.xyz/servers/" + common.StaffServer + "/invite> to join the staff server and <https://fateslist.xyz/servers/" + common.TestServer + "/invite> to join the testing server. Error has been logged to dragon console"
			}

			return "This member has been added successfully"
		},
	}

	commands["RESETVOTES"] = AdminOp{
		InternalName: "resetvotes",
		Cooldown:     types.CooldownBan,
		Description:  "Resets votes for a single bot",
		MinimumPerm:  4,
		Event:        types.EventVoteReset,
		Server:       common.StaffServer,
		Handler: func(context types.SlashContext) string {
			embed := discordgo.MessageEmbed{
				URL:         "https://fateslist.xyz/bot/" + context.Bot.ID,
				Title:       "Bot Vote Reset",
				Description: context.Bot.Mention() + " has had its votes reset!",
				Color:       embedColorBad,
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

			_, err := context.Postgres.Exec(context.Context, "UPDATE bots SET votes = 0 WHERE bot_id = $1", context.Bot.ID)
			if err != nil {
				log.Error(err)
				return err.Error()
			}

			return ""
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
