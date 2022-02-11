package squirrelflight

import (
	"flamepaw/common"
	"flamepaw/slashbot"
	"flamepaw/types"
	"flamepaw/webserver"
	"strconv"
	"strings"

	"github.com/Fates-List/discordgo"
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

			_, res := webserver.VoteBot(context.Postgres, context.Redis, context.User.ID, botId, false)
			return res
		},
	}
	return commands
}
