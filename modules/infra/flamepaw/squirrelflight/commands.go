package squirrelflight

import (
	"flamepaw/common"
	"flamepaw/slashbot"
	"flamepaw/types"
	"flamepaw/webserver"
	"strconv"
	"strings"

	"github.com/Fates-List/discordgo"
	"github.com/jackc/pgtype"
	log "github.com/sirupsen/logrus"
)

func CmdInit() map[string]types.SlashCommand {
	commands := make(map[string]types.SlashCommand)
	commands["vote"] = types.SlashCommand{
		Name:        "vote",
		CmdName:     "vote",
		Description: "Vote for a bot",
		Cooldown:    types.CooldownVote,
		Options: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionUser,
				Name:        "bot",
				Description: "The bot to vote for",
				Required:    true,
			},
		},
		Handler: func(context types.SlashContext) string {
			log.Info("Got command")
			bot := slashbot.GetArg(common.DiscordSquirrelflight, context.Interaction, "bot", false)
			botVal, ok := bot.(*discordgo.User)
			var botId string

			if !ok {
				if context.Interaction.Token == "prefixCmd" {
					if !strings.Contains(context.Interaction.Message.Content, ":") {
						dat := strings.Split(context.Interaction.Message.Content, " ")
						if len(dat) > 1 {
							bot = dat[1]
						}
					}
				}
				botId, ok = bot.(string)
				if !ok {
					return "Could not find bot\nHINT: (its +vote bot:<MENTION BOT HERE>"
				}
				botId = strings.Replace(strings.Replace(strings.Replace(strings.Replace(strings.Replace(botId, "<", "", -1), "!", "", -1), "@", "", -1), ">", "", -1), "&", "", -1)
				if _, err := strconv.Atoi(botId); err != nil {
					if strings.Contains(botId, "#") {
						// Handle # bots too
						if context.AppCmdData.Resolved != nil {
							if len(context.AppCmdData.Resolved.Members) > 0 {
								for _, member := range context.AppCmdData.Resolved.Members {
									botId = member.User.ID
									break
								}
							}
						}
					} else {
						return "Invalid bot ID\nHINT: (its +vote bot:<MENTION BOT HERE>" + botId
					}
				}
			} else {
				botId = botVal.ID
			}

			ok, res := webserver.VoteBot(context.Postgres, context.Redis, context.User.ID, botId, false)

			// Check if they have signed up vote reminders
			var voteReminders pgtype.TextArray

			err := context.Postgres.QueryRow(context.Context, "SELECT vote_reminders::text[] FROM users WHERE user_id = $1", context.User.ID).Scan(&voteReminders)
			if err != nil {
				log.Error(err)
				voteReminders = pgtype.TextArray{
					Elements: []pgtype.Text{},
					Status:   pgtype.Null,
				}
			}

			var hasRemindersEnabled bool
			for _, bot := range voteReminders.Elements {
				if bot.String == botId {
					hasRemindersEnabled = true
					break
				}
			}

			if !hasRemindersEnabled {
				res += "\n\nWant to be reminded when you can next vote for this bot?"

				slashbot.SendIResponseFull(
					common.DiscordMain,
					context.Interaction,
					res,
					true,
					0,
					[]string{},
					nil,
					[]discordgo.MessageComponent{
						discordgo.ActionsRow{
							Components: []discordgo.MessageComponent{
								discordgo.Button{
									CustomID: "vr-enable::" + botId,
									Label:    "Enable Vote Reminders",
								},
							},
						},
					})
				return ""
			}

			return res
		},
	}

	commands["votereminders"] = types.SlashCommand{
		Name:        "votereminders",
		CmdName:     "votereminders",
		Description: "Get and update your vote reminders!",
		Cooldown:    types.CooldownNone,
		Handler: func(context types.SlashContext) string {
			// Check if they have signed up vote reminders
			var voteReminders pgtype.TextArray

			err := context.Postgres.QueryRow(context.Context, "SELECT vote_reminders::text[] FROM users WHERE user_id = $1", context.User.ID).Scan(&voteReminders)
			if err != nil {
				log.Error(err)
				voteReminders = pgtype.TextArray{
					Elements: []pgtype.Text{},
					Status:   pgtype.Null,
				}
			}

			var reminders []string
			var remindersSelect []discordgo.SelectMenuOption
			for _, bot := range voteReminders.Elements {
				botV, err, _ := common.FetchUserRNG(bot.String)
				if err != nil {
					return err.Error()
				}
				if len(botV.Username) > 25 {
					botV.Username = botV.Username[:22] + "..."
				}
				remindersSelect = append(remindersSelect, discordgo.SelectMenuOption{
					Label:       botV.Username,
					Description: bot.String,
					Value:       bot.String,
				})
				reminders = append(reminders, botV.Username+" ("+bot.String+")")
			}
			slashbot.SendIResponseFull(
				common.DiscordMain,
				context.Interaction,
				"**Vote Reminders**\n"+strings.Join(reminders, ", ")+"\nYou can disable a vote reminder below!",
				true,
				0,
				[]string{},
				nil,
				[]discordgo.MessageComponent{
					discordgo.ActionsRow{
						Components: []discordgo.MessageComponent{
							discordgo.SelectMenu{
								CustomID:    "vr-menu",
								Placeholder: "Select a vote reminder to disable",
								Options:     remindersSelect,
								MinValues:   1,
								MaxValues:   1,
							},
						},
					},
				},
			)
			return ""
		},
	}

	commands["channelid"] = types.SlashCommand{
		Name:        "channelid",
		CmdName:     "channelid",
		Description: "Get the ID of the current channel",
		Cooldown:    types.CooldownNone,
		Handler: func(context types.SlashContext) string {
			if context.Interaction.ChannelID == "" {
				return "Not in a channel?"
			}
			return context.Interaction.ChannelID
		},
	}

	return commands
}
