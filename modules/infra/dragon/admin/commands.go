package admin

import (
	"context"
	"dragon/common"
	"dragon/slashbot"
	"dragon/types"
	"encoding/json"
	"io"
	"net/http"
	"strconv"
	"time"

	"github.com/Fates-List/discordgo"
	"github.com/davecgh/go-spew/spew"
	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

const good = 0x00ff00
const bad = 0xe74c3c
const perMessageQueueCount = 4 // 4 bots per message

var (
	commands         = make(map[string]types.AdminOp)
	commandNameCache = make(map[string]string)
)

func autocompleter(state int) func(context types.HandlerData) (ac []*discordgo.ApplicationCommandOptionChoice) {
	return func(context types.HandlerData) (ac []*discordgo.ApplicationCommandOptionChoice) {
		dataVal := slashbot.GetArg(context.Discord, context.Interaction, "bot", false)
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
				user, err := context.Discord.User(botId.String)
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
	commands["QUEUE"] = types.AdminOp{
		InternalName: "queue",
		Cooldown:     types.CooldownNone,
		Description:  "Lists the Fates List bot queue",
		Event:        types.EventNone,
		MinimumPerm:  1,
		SlashRaw:     true,
		Server:       common.TestServer,
		SlashOptions: []*discordgo.ApplicationCommandOption{},
		Handler: func(context types.AdminContext) string {
			bots, err := context.Postgres.Query(context.Context, "SELECT bots.bot_id::text, bots.prefix, bots.description, bots.guild_count::text, bot_owner.owner::text FROM bots INNER JOIN bot_owner ON bots.bot_id = bot_owner.bot_id WHERE bots.state = $1 AND bot_owner.main = true ORDER BY bots.guild_count DESC", types.BotStatePending.Int())
			if err != nil {
				return err.Error()
			}
			defer bots.Close()

			currBot := 1

			var output string

			var iterOnce bool
			for bots.Next() {
				iterOnce = true
				var botId pgtype.Text
				var prefix pgtype.Text
				var description pgtype.Text
				var guildCount pgtype.Text
				var botOwner pgtype.Text
				err := bots.Scan(&botId, &prefix, &description, &guildCount, &botOwner)
				if err != nil {
					return err.Error() + " in iteration " + strconv.Itoa(currBot)
				}
				if guildCount.String == "0" {
					guildCount.String = "Unknown"
				}
				if prefix.Status != pgtype.Present {
					prefix = pgtype.Text{String: "This bot uses slash commands", Status: pgtype.Present}
				} else if prefix.String == "" {
					prefix.String = "This bot uses slash commands"
				}

				botUser, err := context.Discord.User(botId.String)

				if err != nil {
					botUser = &discordgo.User{Username: "Unknown", Discriminator: "0000"}
				}

				output += "**" + strconv.Itoa(currBot) + ".** " + botUser.Username + "#" + botUser.Discriminator + "\n**Prefix:** " + prefix.String + "\n**Description:** " + description.String + "\n**Guild Count (approx.):** " + guildCount.String + "\n**Invite:** " + "<https://fateslist.xyz/bot/" + botId.String + "/invite>\n" + "**Main Owner:** " + botOwner.String + "\n\n"
				if currBot%perMessageQueueCount == 0 {
					slashbot.SendIResponse(context.Discord, context.Interaction, output, false)
					output = ""
				}
				currBot += 1
			}

			if !iterOnce {
				return "Darkstripe says there are no bots in queue, he's probably right *grumble* *grumble*..."
			}

			if output != "" {
				slashbot.SendIResponse(context.Discord, context.Interaction, output, false)
			}
			slashbot.SendIResponse(context.Discord, context.Interaction, "nop", true)

			return "nop"
		},
	}

	commands["USERSTATE"] = types.AdminOp{
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
		Handler: func(context types.AdminContext) string {
			stateVal := slashbot.GetArg(context.Discord, context.Interaction, "state", false)
			state, ok := stateVal.(int64)
			if !ok {
				return "Invalid state"
			}
			userVal := slashbot.GetArg(context.Discord, context.Interaction, "user", false)
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

	commands["MOCK"] = types.AdminOp{
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
	commands["RESETVOTESALL"] = types.AdminOp{
		InternalName: "resetallvotes",
		Cooldown:     types.CooldownNone,
		Description:  "Reset votes for all bots on the list",
		MinimumPerm:  6,
		ReasonNeeded: false,
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
		Handler: func(context types.AdminContext) string {
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
			embed := discordgo.MessageEmbed{
				URL:         "https://fateslist.xyz",
				Title:       "All Bot Votes Reset",
				Description: "All bots have had its votes reset!",
				Color:       good,
				Fields: []*discordgo.MessageEmbedField{
					{
						Name:  "Reason",
						Value: context.Reason,
					},
				},
			}
			context.Discord.ChannelMessageSendComplex(common.SiteLogs, &discordgo.MessageSend{
				Embed: &embed,
			})
			return "OK. But make sure to clear the database to get rid of existing vote locks"
		},
	}

	commands["GETACCESS"] = types.AdminOp{
		InternalName: "getaccess",
		Cooldown:     types.CooldownBan,
		Description:  "Get access to the staff server",
		MinimumPerm:  0,
		SlashRaw:     true,
		Event:        types.EventNone,
		Server:       common.StaffServer,
		SlashOptions: []*discordgo.ApplicationCommandOption{},
		Handler: func(context types.AdminContext) string {
			if context.StaffPerm < 2 {
				time.AfterFunc(3*time.Second, func() {
					err := context.Discord.GuildMemberDeleteWithReason(common.StaffServer, context.User.ID, "Kicked due to not being a staff member")
					if err != nil {
						context.Discord.ChannelMessageSendComplex(context.Interaction.ChannelID, &discordgo.MessageSend{
							Content: "@everyone **I could not kick " + context.User.Mention() + ". Please kick them when you have time as they are not a staff member!**",
						})
					}
				})
				return "You are not a Fates List Staff Member. You will hence be kicked from the staff server!"
			}

			context.Discord.GuildMemberRoleAdd(common.StaffServer, context.User.ID, common.AccessGrantedRole)
			// Get correct role with needed perm
			for _, v := range common.StaffRoles {
				if v.Perm == context.StaffPerm {
					context.Discord.GuildMemberRoleAdd(common.StaffServer, context.User.ID, v.StaffID)
				}
			}

			return "Welcome back... master!"
		},
	}

	commands["WHITELISTBOT"] = types.AdminOp{
		InternalName: "whitelistbot",
		Cooldown:     types.CooldownLock,
		Description:  "Adds a bot to the Fates List staff server whitelist temporarily so it can be added",
		MinimumPerm:  4,
		Event:        types.EventNone,
		Server:       common.StaffServer,
		SlashRaw:     true,
		ReasonNeeded: true,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionUser,
				Name:        "bot",
				Description: "The bot to whitelist",
				Required:    true,
			},
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "reason",
				Description: "Why do you wish for this bot to be whitelisted. May be audited in the future!",
				Required:    true,
			},
		},
		Handler: func(context types.AdminContext) string {
			userVal := slashbot.GetArg(context.Discord, context.Interaction, "bot", false)
			user, ok := userVal.(*discordgo.User)
			if !ok {
				return "This user could not be found..."
			} else if !user.Bot {
				return "You can only whitelist bots! Users arent affected by Silverpelt Bot Defense!"
			}
			botWhitelist[user.ID] = true
			time.AfterFunc(1*time.Minute, func() {
				log.Info("Removed user " + user.ID + " from whitelist")
				botWhitelist[user.ID] = false
			})
			return "Done"
		},
	}

	// Adds a staff to our team!
	commands["ADDSTAFF"] = types.AdminOp{
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
		Handler: func(context types.AdminContext) string {
			userVal := slashbot.GetArg(context.Discord, context.Interaction, "user", false)
			user, ok := userVal.(*discordgo.User)
			if !ok {
				return "This user could not be found..."
			} else if user.Bot {
				return "You can't add bots to the staff team!"
			}

			// Check if the user in question is in the main server
			if _, err := context.Discord.State.Member(common.MainServer, user.ID); err != nil {
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

			err := context.Discord.GuildMemberRoleAdd(common.MainServer, user.ID, commStaff.ID)
			if err != nil {
				return "Failed to give community staff role. Do I have perms? Is the role ID correct?"
			}

			err = context.Discord.GuildMemberRoleAdd(common.MainServer, user.ID, botReviewer.ID)
			if err != nil {
				return "Failed to give bot reviewer role. Do I have perms? Is the role ID correct?"
			}

			userDm, err := context.Discord.UserChannelCreate(user.ID)

			_, err2 := context.Discord.ChannelMessageSendComplex(userDm.ID, &discordgo.MessageSend{
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

	commands["RESETVOTES"] = types.AdminOp{
		InternalName: "resetvotes",
		Cooldown:     types.CooldownBan,
		Description:  "Resets votes for a single bot",
		MinimumPerm:  4,
		ReasonNeeded: true,
		Event:        types.EventVoteReset,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "reason",
				Description: "Reason for resetting the votes for this bot",
				Required:    true,
			},
		},
		Server: common.StaffServer,
		Handler: func(context types.AdminContext) string {
			embed := discordgo.MessageEmbed{
				URL:         "https://fateslist.xyz/bot/" + context.Bot.ID,
				Title:       "Bot Vote Reset",
				Description: context.Bot.Mention() + " has had its votes reset!",
				Color:       bad,
				Fields: []*discordgo.MessageEmbedField{
					{
						Name:  "Reason",
						Value: context.Reason,
					},
				},
			}
			context.Discord.ChannelMessageSendComplex(common.SiteLogs, &discordgo.MessageSend{
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

	// Requeue
	commands["REQUEUE"] = types.AdminOp{
		InternalName: "requeue",
		Cooldown:     types.CooldownRequeue,
		Description:  "Requeue a bot",
		MinimumPerm:  3,
		ReasonNeeded: true,
		Event:        types.EventBotRequeue,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "reason",
				Description: "Reason for requeuing the bot",
				Required:    true,
			},
		},
		Server:        common.TestServer,
		Autocompleter: autocompleter(types.BotStateDenied.Int()),
		Handler: func(context types.AdminContext) string {
			if context.BotState != types.BotStateDenied {
				return "This bot cannot be requeued as it is not currently denied"
			}

			embed := discordgo.MessageEmbed{
				URL:         "https://fateslist.xyz/bot/" + context.Bot.ID,
				Title:       "Bot Requeued",
				Description: context.Bot.Mention() + " has been requeued (removed from the deny list)!",
				Color:       good,
				Fields: []*discordgo.MessageEmbedField{
					{
						Name:  "Reason",
						Value: context.Reason,
					},
				},
			}
			context.Discord.ChannelMessageSendComplex(common.SiteLogs, &discordgo.MessageSend{
				Embed: &embed,
			})
			_, err := context.Postgres.Exec(context.Context, "UPDATE bots SET state = $1 WHERE bot_id = $2", types.BotStatePending.Int(), context.Bot.ID)
			if err != nil {
				log.Error(err)
				return err.Error()
			}

			return ""
		},
	}
	// Claim
	commands["CLAIM"] = types.AdminOp{
		InternalName:  "claim",
		Cooldown:      types.CooldownNone,
		Description:   "Claim a bot",
		MinimumPerm:   2,
		ReasonNeeded:  false,
		Event:         types.EventBotClaim,
		SlashOptions:  []*discordgo.ApplicationCommandOption{},
		Server:        common.TestServer,
		Autocompleter: autocompleter(types.BotStatePending.Int()),
		Handler: func(context types.AdminContext) string {
			if context.BotState != types.BotStatePending {
				return "This bot cannot be claimed as it is not currently pending review or it is already under review"
			}

			embed := discordgo.MessageEmbed{
				URL:         "https://fateslist.xyz/bot/" + context.Bot.ID,
				Title:       "Bot Under Review",
				Description: context.Bot.Mention() + " is now under review by " + context.User.Mention() + " and should be approved or denied soon!",
				Color:       good,
			}
			_, err := context.Discord.ChannelMessageSendComplex(common.SiteLogs, &discordgo.MessageSend{
				Content: "<@" + context.Owner + ">",
				Embed:   &embed,
			})

			if err != nil {
				log.Warn(err)
			}

			_, err = context.Postgres.Exec(context.Context, "UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", types.BotStateUnderReview.Int(), context.User.ID, context.Bot.ID)

			go UpdateBotLogs(context.Context, context.Postgres, context.User.ID, context.Bot.ID, types.UserBotApprove)

			if err != nil {
				log.Error(err)
			}

			return ""
		},
	}

	// Unclaim
	commands["UNCLAIM"] = types.AdminOp{
		InternalName:  "unclaim",
		Cooldown:      types.CooldownNone,
		Description:   "Unclaim a bot",
		MinimumPerm:   2,
		ReasonNeeded:  false,
		Event:         types.EventBotUnclaim,
		SlashOptions:  []*discordgo.ApplicationCommandOption{},
		Server:        common.TestServer,
		Autocompleter: autocompleter(types.BotStateUnderReview.Int()),
		Handler: func(context types.AdminContext) string {
			if context.BotState != types.BotStateUnderReview {
				return "This bot cannot be unclaimed as it is not currently under review"
			}

			embed := discordgo.MessageEmbed{
				URL:         "https://fateslist.xyz/bot/" + context.Bot.ID,
				Title:       "Bot Unclaimed",
				Description: context.Bot.Mention() + " has been unclaimed by " + context.User.Mention() + ". It is no longer under review right now but it should be approved or denied when another reviewer comes in! Don't worry, this is completely normal!",
				Color:       good,
			}
			_, err := context.Discord.ChannelMessageSendComplex(common.SiteLogs, &discordgo.MessageSend{
				Embed: &embed,
			})

			if err != nil {
				log.Warn(err)
			}

			_, err = context.Postgres.Exec(context.Context, "UPDATE bots SET state = $1 WHERE bot_id = $2", types.BotStatePending.Int(), context.Bot.ID)

			go UpdateBotLogs(context.Context, context.Postgres, context.User.ID, context.Bot.ID, types.UserBotUnclaim)

			if err != nil {
				log.Error(err)
			}

			return ""
		},
	}

	// Ban
	commands["BAN"] = types.AdminOp{
		InternalName: "ban",
		Cooldown:     types.CooldownBan,
		Description:  "Bans a bot",
		MinimumPerm:  3,
		ReasonNeeded: true,
		Event:        types.EventBotBan,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "reason",
				Description: "Reason to ban the bot",
				Required:    true,
			},
		},
		Server:        common.StaffServer,
		Autocompleter: autocompleter(types.BotStateApproved.Int()),
		Handler: func(context types.AdminContext) string {
			if context.BotState == types.BotStateCertified {
				return "You can't ban certified botd! Uncertify them first!"
			}

			embed := discordgo.MessageEmbed{
				URL:         "https://fateslist.xyz/bot/" + context.Bot.ID,
				Title:       "Bot Banned",
				Description: context.Bot.Mention() + " has been banned by " + context.User.Mention() + ".",
				Color:       bad,
				Fields: []*discordgo.MessageEmbedField{
					{
						Name:  "Reason",
						Value: context.Reason,
					},
				},
			}
			_, err := context.Discord.ChannelMessageSendComplex(common.SiteLogs, &discordgo.MessageSend{
				Content: "<@" + context.Owner + ">",
				Embed:   &embed,
			})

			if err != nil {
				log.Warn(err)
			}
			_, err = context.Postgres.Exec(context.Context, "UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", types.BotStateBanned.Int(), context.User.ID, context.Bot.ID)

			go UpdateBotLogs(context.Context, context.Postgres, context.User.ID, context.Bot.ID, types.UserBotBan)

			if err != nil {
				log.Error(err)
				return "PostgreSQL error: " + err.Error()
			}

			err = context.Discord.GuildBanCreateWithReason(common.MainServer, context.Bot.ID, context.Reason, 0)

			if err != nil {
				return "OK. Bot was banned successfully but it could not be kicked due to reason: " + err.Error()
			}
			return ""
		},
	}

	// Unban
	commands["UNBAN"] = types.AdminOp{
		InternalName: "unban",
		Cooldown:     types.CooldownBan,
		Description:  "Unbans a bot",
		MinimumPerm:  3,
		ReasonNeeded: true,
		Event:        types.EventBotUnban,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "reason",
				Description: "Reason to unban the bot",
				Required:    true,
			},
		},
		Server:        common.StaffServer,
		Autocompleter: autocompleter(types.BotStateBanned.Int()),
		Handler: func(context types.AdminContext) string {
			embed := discordgo.MessageEmbed{
				URL:         "https://fateslist.xyz/bot/" + context.Bot.ID,
				Title:       "Bot Unbanned",
				Description: context.Bot.Mention() + " has been unbanned by " + context.User.Mention() + ".",
				Color:       good,
				Fields: []*discordgo.MessageEmbedField{
					{
						Name:  "Extra Info/Reason",
						Value: context.Reason,
					},
				},
			}
			_, err := context.Discord.ChannelMessageSendComplex(common.SiteLogs, &discordgo.MessageSend{
				Content: "<@" + context.Owner + ">",
				Embed:   &embed,
			})

			if err != nil {
				log.Warn(err)
			}

			_, err = context.Postgres.Exec(context.Context, "UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", types.BotStateApproved.Int(), context.User.ID, context.Bot.ID)

			if err != nil {
				log.Error(err)
				return "Got an error when trying to update the database. Please report this: " + err.Error()
			}

			context.Discord.GuildBanDelete(common.MainServer, context.Bot.ID)
			return ""
		},
	}

	// Certify
	commands["CERTIFY"] = types.AdminOp{
		InternalName:  "certify",
		Cooldown:      types.CooldownNone,
		Description:   "Certifies a bot",
		MinimumPerm:   5,
		ReasonNeeded:  false,
		Event:         types.EventBotCertify,
		SlashOptions:  []*discordgo.ApplicationCommandOption{},
		Server:        common.StaffServer,
		Autocompleter: autocompleter(types.BotStateApproved.Int()),
		Handler: func(context types.AdminContext) string {
			var errors string = "OK. "
			if context.BotState != types.BotStateApproved {
				return "This bot cannot be certified as it is not approved or is already certified"
			}

			embed := discordgo.MessageEmbed{
				URL:         "https://fateslist.xyz/bot/" + context.Bot.ID,
				Title:       "Bot Certified",
				Description: context.Bot.Mention() + " has been certified by " + context.User.Mention() + ". Congratulations on your accompishment :heart:",
				Color:       good,
			}
			_, err := context.Discord.ChannelMessageSendComplex(common.SiteLogs, &discordgo.MessageSend{
				Content: "<@" + context.Owner + ">",
				Embed:   &embed,
			})

			if err != nil {
				log.Warn(err)
			}

			_, err = context.Postgres.Exec(context.Context, "UPDATE bots SET state = $1 WHERE bot_id = $3", types.BotStateCertified.Int(), context.Bot.ID)

			go UpdateBotLogs(context.Context, context.Postgres, context.User.ID, context.Bot.ID, types.UserBotCertify)

			if err != nil {
				log.Error(err)
			}

			err = context.Discord.GuildMemberRoleAdd(common.MainServer, context.Bot.ID, common.CertifiedBotRole)

			if err != nil {
				errors += err.Error() + "\n"
			}

			// Give certified bot role
			owners, err := context.Postgres.Query(context.Context, "SELECT owner FROM bot_owner WHERE bot_id = $1", context.Bot.ID)

			if err != nil {
				errors += "Bot was certified, but I could not find bot owners because: " + err.Error() + "\n"
				return "OK. Bot was certified, but I could not add certified dev role to bot owners because: \n" + errors
			}

			defer owners.Close()

			var i int

			for owners.Next() {
				i += 1
				var owner pgtype.Int8
				err = owners.Scan(&owner)
				if err != nil {
					errors += "Got error: " + err.Error() + " in iteration " + strconv.Itoa(i) + " (user id is unknown)\n"
					continue
				}

				if owner.Status != pgtype.Present {
					errors += "Got error: Owner is NULL in iteration" + strconv.Itoa(i) + "\n"
					continue
				}

				err = context.Discord.GuildMemberRoleAdd(common.MainServer, strconv.FormatInt(owner.Int, 10), common.CertifiedDevRole)
				if err != nil {
					errors += "Got error: " + err.Error() + " in iteration " + strconv.Itoa(i) + "and user id (" + strconv.FormatInt(owner.Int, 10) + ")\n"
					continue
				}
			}
			return errors
		},
	}

	// Uncertify
	commands["UNCERTIFY"] = types.AdminOp{
		InternalName: "uncertify",
		Cooldown:     types.CooldownNone,
		Description:  "Uncertifies a bot.",
		MinimumPerm:  5,
		ReasonNeeded: true,
		Event:        types.EventBotUncertify,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "reason",
				Description: "Reason for uncertifying this bot",
				Required:    true,
			},
		},
		Server:        common.StaffServer,
		Autocompleter: autocompleter(types.BotStateCertified.Int()),
		Handler: func(context types.AdminContext) string {
			var errors string = "OK. "
			if context.BotState != types.BotStateCertified {
				return "This bot cannot be uncertified as it is not currently certified"
			}

			embed := discordgo.MessageEmbed{
				URL:         "https://fateslist.xyz/bot/" + context.Bot.ID,
				Title:       "Bot Uncertified",
				Description: context.Bot.Mention() + " has been uncertified by " + context.User.Mention() + ".",
				Color:       bad,
				Fields: []*discordgo.MessageEmbedField{
					{
						Name:  "Reason",
						Value: context.Reason,
					},
				},
			}
			_, err := context.Discord.ChannelMessageSendComplex(common.SiteLogs, &discordgo.MessageSend{
				Content: "<@" + context.Owner + ">",
				Embed:   &embed,
			})

			if err != nil {
				log.Warn(err)
			}

			_, err = context.Postgres.Exec(context.Context, "UPDATE bots SET state = $1 WHERE bot_id = $2", types.BotStateApproved.Int(), context.Bot.ID)

			if err != nil {
				log.Error(err)
			}

			err = context.Discord.GuildMemberRoleRemove(common.MainServer, context.Bot.ID, common.CertifiedBotRole)

			if err != nil {
				errors += "Failed to remove certified bot role because: " + err.Error() + "\n"
			}
			return ""
		},
	}

	// Approve
	commands["APPROVE"] = types.AdminOp{
		InternalName: "approve",
		Cooldown:     types.CooldownNone,
		Description:  "Approves a bot",
		MinimumPerm:  2,
		ReasonNeeded: true,
		Event:        types.EventBotApprove,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "reason",
				Description: "Feedback about the bot and/or a welcome message",
				Required:    true,
			},
			/* DG1 {
				Type:        discordgo.ApplicationCommandOptionInteger,
				Name:        "guild_count",
				Description: "Guild count of the bot currently",
				Required:    true,
			}, */
		},
		Server:        common.TestServer,
		Autocompleter: autocompleter(types.BotStateUnderReview.Int()),
		Handler: func(context types.AdminContext) string {
			if context.BotState != types.BotStateUnderReview {
				return "This bot cannot be approved as it is not currently under review. Did you claim it first?"
			} /* DG1 else if context.ExtraContext == nil {
				return "Bots approximate guild count must be set when approving"
			}
			guildCountVal := slashbot.GetArg(context.Discord, context.Interaction, "guild_count", false)
			guildCount, ok := guildCount.(int)
			if !ok {
				return "Could not parse guild count: " + err.Error()
			} */

			client := http.Client{Timeout: 15 * time.Second}
			gcResp, err := client.Get("https://japi.rest/discord/v1/application/" + context.Bot.ID)
			if err != nil {
				return err.Error()
			}
			if gcResp.StatusCode != 200 {
				return "japi.rest returned a non-success status code when getting the approximate guild count. Please report this error to skylar#6666 if this happens after retrying!\n\n" + gcResp.Status
			}
			defer gcResp.Body.Close()

			body, err := io.ReadAll(gcResp.Body)
			if err != nil {
				return err.Error()
			}

			var appData types.JAPIApp

			err = json.Unmarshal(body, &appData)

			if err != nil {
				return err.Error()
			}

			guildCount := appData.Data.Bot.ApproximateGuildCount

			var errors string = "OK. \n**Invite (should work, if not just use the bot pages invite): https://discord.com/api/oauth2/authorize?permissions=0&scope=bot%20applications.commands&client_id=" + context.Bot.ID + "**\n\n"

			embed := discordgo.MessageEmbed{
				URL:         "https://fateslist.xyz/bot/" + context.Bot.ID,
				Title:       "Bot Approved",
				Description: context.Bot.Mention() + " has been approved by " + context.User.Mention() + ". Congratulations on your accompishment :heart:",
				Color:       good,
				Fields: []*discordgo.MessageEmbedField{
					{
						Name:  "Feedback",
						Value: context.Reason,
					},
				},
			}
			_, err = context.Discord.ChannelMessageSendComplex(common.SiteLogs, &discordgo.MessageSend{
				Content: "<@" + context.Owner + ">",
				Embed:   &embed,
			})

			if err != nil {
				log.Warn(err)
			}

			_, err = context.Postgres.Exec(context.Context, "UPDATE bots SET state = $1, verifier = $2, guild_count = $3 WHERE bot_id = $4", types.BotStateApproved.Int(), context.User.ID, guildCount, context.Bot.ID)

			go UpdateBotLogs(context.Context, context.Postgres, context.User.ID, context.Bot.ID, types.UserBotApprove)

			if err != nil {
				log.Error(err)
				return "Got an error when trying to update the database. Please report this: " + err.Error()
			}

			// Give bot bot role
			owners, err := context.Postgres.Query(context.Context, "SELECT owner FROM bot_owner WHERE bot_id = $1", context.Bot.ID)

			if err != nil {
				errors += "Could not find bot owners because: " + err.Error() + "\n"
				return "OK. Bot was approved, but I could not add bot dev role to bot owners because: \n" + errors
			}

			defer owners.Close()

			var i int

			for owners.Next() {
				i += 1
				var owner pgtype.Int8
				err = owners.Scan(&owner)
				if err != nil {
					errors += "Got error: " + err.Error() + " in iteration " + strconv.Itoa(i) + " (user id is unknown)\n"
					continue
				}

				if owner.Status != pgtype.Present {
					errors += "Got error: Owner is NULL in iteration" + strconv.Itoa(i) + "\n"
					continue
				}

				err = context.Discord.GuildMemberRoleAdd(common.MainServer, strconv.FormatInt(owner.Int, 10), common.BotDevRole)
				if err != nil {
					errors += "Got error: " + err.Error() + " in iteration " + strconv.Itoa(i) + " and user id (" + strconv.FormatInt(owner.Int, 10) + ")\n"
					continue
				}
			}

			return errors
		},
	}

	// Denies a bot
	commands["DENY"] = types.AdminOp{
		InternalName: "deny",
		Cooldown:     types.CooldownNone,
		Description:  "Denies a bot",
		MinimumPerm:  2,
		ReasonNeeded: true,
		Event:        types.EventBotDeny,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "reason",
				Description: "Reason for denying the bot",
				Required:    true,
			},
		},
		Server:        common.TestServer,
		Autocompleter: autocompleter(types.BotStateUnderReview.Int()),
		Handler: func(context types.AdminContext) string {
			if context.BotState != types.BotStateUnderReview {
				return "This bot cannot be denied as it is not currently under review. Did you claim it first?"
			}

			embed := discordgo.MessageEmbed{
				URL:         "https://fateslist.xyz/bot/" + context.Bot.ID,
				Title:       "Bot Denied",
				Description: context.Bot.Mention() + " has been denied by " + context.User.Mention() + ".",
				Color:       bad,
				Fields: []*discordgo.MessageEmbedField{
					{
						Name:  "Reason",
						Value: context.Reason,
					},
				},
			}
			_, err := context.Discord.ChannelMessageSendComplex(common.SiteLogs, &discordgo.MessageSend{
				Content: "<@" + context.Owner + ">",
				Embed:   &embed,
			})

			if err != nil {
				log.Warn(err)
			}

			_, err = context.Postgres.Exec(context.Context, "UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", types.BotStateDenied.Int(), context.User.ID, context.Bot.ID)

			go UpdateBotLogs(context.Context, context.Postgres, context.User.ID, context.Bot.ID, types.UserBotDeny)

			if err != nil {
				log.Error(err)
			}

			return ""
		},
	}

	// Unverifies a bot
	commands["UNVERIFY"] = types.AdminOp{
		InternalName: "unverify",
		Cooldown:     types.CooldownNone,
		Description:  "Unverifies a bot",
		MinimumPerm:  2,
		ReasonNeeded: true,
		Event:        types.EventBotUnverify,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "reason",
				Description: "Reason for unverifying the bot",
				Required:    true,
			},
		},
		Server:        common.StaffServer,
		Autocompleter: autocompleter(types.BotStateApproved.Int()),
		Handler: func(context types.AdminContext) string {
			if context.BotState != types.BotStateApproved {
				return "This bot cannot be unverified as it is not currently approved or is certified."
			}

			embed := discordgo.MessageEmbed{
				URL:         "https://fateslist.xyz/bot/" + context.Bot.ID,
				Title:       "Bot Unverified",
				Description: context.Bot.Mention() + " has been unverified by " + context.User.Mention() + ".",
				Color:       bad,
				Fields: []*discordgo.MessageEmbedField{
					{
						Name:  "Reason",
						Value: context.Reason,
					},
				},
			}
			_, err := context.Discord.ChannelMessageSendComplex(common.SiteLogs, &discordgo.MessageSend{
				Content: "<@" + context.Owner + ">",
				Embed:   &embed,
			})

			if err != nil {
				log.Warn(err)
			}

			_, err = context.Postgres.Exec(context.Context, "UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", types.BotStateUnderReview.Int(), context.User.ID, context.Bot.ID)

			if err != nil {
				log.Error(err)
			}

			return ""
		},
	}

	commands["STAFFLOCK"] = types.AdminOp{
		InternalName:  "stafflock",
		Cooldown:      types.CooldownNone,
		Description:   "Staff locks a bot",
		MinimumPerm:   2,
		ReasonNeeded:  false,
		Event:         types.EventStaffLock,
		SlashOptions:  []*discordgo.ApplicationCommandOption{},
		Server:        common.StaffServer,
		Autocompleter: autocompleter(types.BotStateApproved.Int()),
		Handler: func(context types.AdminContext) string {
			countKey := "fl_staff_access-" + context.User.ID + ":count"
			accessKey := "fl_staff_access-" + context.User.ID + ":" + context.Bot.ID

			botLocked := context.Redis.Exists(context.Context, accessKey).Val()
			if botLocked == 0 {
				return "You have not unlocked this bot yet!"
			}
			pipeline := context.Redis.Pipeline()
			pipeline.Decr(context.Context, countKey)
			pipeline.Del(context.Context, accessKey)
			_, err := pipeline.Exec(context.Context)
			if err != nil {
				log.Warn(err)
				return "Something happened! " + err.Error()
			}

			embed := discordgo.MessageEmbed{
				URL:         "https://fateslist.xyz/bot/" + context.Bot.ID,
				Title:       "Staff Lock",
				Description: context.Bot.Mention() + " has been locked by " + context.User.Mention() + ". This is perfectly normal and is a safety measure against hacking and exploits",
				Color:       good,
			}

			_, err = context.Discord.ChannelMessageSendComplex(common.SiteLogs, &discordgo.MessageSend{
				Content: "<@" + context.Owner + ">",
				Embed:   &embed,
			})

			if err != nil {
				log.Warn(err)
			}

			return "Thank you for relocking this bot and keeping Fates List safe"
		},
	}

	commands["STAFFUNLOCK"] = types.AdminOp{
		InternalName: "staffunlock",
		Cooldown:     types.CooldownNone,
		Description:  "Staff unlocks a bot",
		MinimumPerm:  2,
		ReasonNeeded: true,
		Event:        types.EventStaffUnlock,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "reason",
				Description: "Reason you need to staff unlock the bot, is publicly visible",
				Required:    true,
			},
		},
		Server:        common.StaffServer,
		Autocompleter: autocompleter(types.BotStateApproved.Int()),
		Handler: func(context types.AdminContext) string {
			countKey := "fl_staff_access-" + context.User.ID + ":count"
			accessKey := "fl_staff_access-" + context.User.ID + ":" + context.Bot.ID

			botLocked := context.Redis.Exists(context.Context, accessKey).Val()
			if botLocked != 0 {
				return "You have already locked this bot."
			}
			botLockedCount, err := context.Redis.Get(context.Context, countKey).Int()

			if err == nil && botLockedCount > 0 {
				return "You may only have one bot unlocked at any given time!"
			}

			pipeline := context.Redis.Pipeline()

			pipeline.Incr(context.Context, countKey)
			pipeline.Expire(context.Context, countKey, 60*time.Minute)
			pipeline.Set(context.Context, accessKey, "0", 30*time.Minute)
			_, err = pipeline.Exec(context.Context)
			if err != nil {
				log.Warn(err)
				return "Something happened! " + err.Error()
			}

			embed := discordgo.MessageEmbed{
				URL:         "https://fateslist.xyz/bot/" + context.Bot.ID,
				Title:       "Staff Unlock",
				Description: context.Bot.Mention() + " has been unlocked by " + context.User.Mention() + ". This is perfectly normal This is normal but if it happens too much, open a ticket or otherwise contact any online or offline staff immediately",
				Color:       good,
				Fields: []*discordgo.MessageEmbedField{
					{
						Name:  "Reason",
						Value: context.Reason,
					},
				},
			}

			_, err = context.Discord.ChannelMessageSendComplex(common.SiteLogs, &discordgo.MessageSend{
				Content: "<@" + context.Owner + ">",
				Embed:   &embed,
			})

			if err != nil {
				log.Warn(err)
			}

			return "OK. Be **absolutely** *sure* to relock the bot as soon as possible"
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
