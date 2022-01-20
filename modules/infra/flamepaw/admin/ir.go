package admin

// ir.go handles the slash command IR and passes over the admin operation to silverpelt.go

import (
	"flamepaw/common"
	"flamepaw/slashbot"
	"flamepaw/types"
	"strconv"
	"strings"
	"time"

	"github.com/Fates-List/discordgo"
	"github.com/jackc/pgtype"
	log "github.com/sirupsen/logrus"
)

// Prepend is complement to builtin append.
func Prepend[T any](items []T, item T) []T {
	return append([]T{item}, items...)
}

func slashIr() map[string]types.SlashCommand {
	// Add the slash commands IR for use in slashbot. Is used internally by CmdInit
	botIdOption := discordgo.ApplicationCommandOption{
		Type:        discordgo.ApplicationCommandOptionUser,
		Name:        "bot",
		Description: "Bot (either ID or mention)",
		Required:    true,
	}
	botIdOptionAc := discordgo.ApplicationCommandOption{
		Type:         discordgo.ApplicationCommandOptionString,
		Name:         "bot",
		Description:  "Select the bot from the list",
		Required:     true,
		Autocomplete: true,
	}

	var commandsToRet map[string]types.SlashCommand = make(map[string]types.SlashCommand)
	for cmdName, v := range commands {
		if !v.SlashRaw {
			var add discordgo.ApplicationCommandOption
			if v.Autocompleter != nil {
				// Assume bot id option is being autocompleted
				log.Info("Got autocompleter")
				add = botIdOptionAc
			} else {
				add = botIdOption
			}
			v.SlashOptions = Prepend(v.SlashOptions, &add)
		}

		commandsToRet[cmdName] = types.SlashCommand{
			CmdName:       cmdName,
			Name:          v.InternalName,
			Description:   v.Description,
			Cooldown:      v.Cooldown,
			Options:       v.SlashOptions,
			Server:        v.Server,
			Autocompleter: v.Autocompleter,
			Handler: func(context types.SlashContext) string {
				var op string = commandNameCache[context.AppCmdData.Name]

				if op == "" {
					return ""
				}

				// Now for the admin checks and other code
				adminOp, ok := commands[op]
				if !ok {
					return "This bot operation does not exist (" + op + ")."
				}

				botVal := slashbot.GetArg(common.DiscordMain, context.Interaction, "bot", false)
				botId, ok := botVal.(string)

				if !ok && !adminOp.SlashRaw {
					botUser, ok := botVal.(*discordgo.User)
					if !ok {
						return "No Bot ID provided"
					}
					botId = botUser.ID
				}

				reasonVal := slashbot.GetArg(common.DiscordMain, context.Interaction, "reason", true)
				reason, ok := reasonVal.(string)

				if !ok {
					reason = ""
				}

				if context.MockMode {
					return "Please exit mock mode and try again!"
				}

				if !adminOp.Critical {
					verify, err := context.Redis.Get(context.Context, "staffverify:"+context.User.ID).Result()
					if err != nil || verify != common.VerificationCode(context.User.ID) {
						return "You must verify in the staff server again to ensure you are up to date with our rules and staff guide"
					}
				}

				if context.StaffPerm < adminOp.MinimumPerm {
					return "This operation requires perm: " + strconv.Itoa(int(adminOp.MinimumPerm)) + " but you only have perm number " + strconv.Itoa(int(context.StaffPerm)) + ".\nUser ID: " + context.User.ID
				}

				if adminOp.ReasonNeeded && len(reason) < 3 {
					return "You must specify a reason for doing this!"
				}

				var state pgtype.Int4
				var owner pgtype.Int8
				var botIdReal pgtype.Text
				context.Postgres.QueryRow(context.Context, "SELECT state, bot_id::text FROM bots WHERE bot_id = $1 OR client_id = $1", botId).Scan(&state, &botIdReal)

				// These checks do not apply for slashRaw
				if !adminOp.SlashRaw {
					if state.Status != pgtype.Present {
						return "This bot does not exist!"
					}

					context.Postgres.QueryRow(context.Context, "SELECT owner FROM bot_owner WHERE bot_id = $1 AND main = true", botId).Scan(&owner)

					if owner.Status != pgtype.Present && botId != "" {
						context.Postgres.Exec(context.Context, "DELETE FROM bot_owner WHERE bot_id = $1", botId)
						context.Postgres.Exec(context.Context, "INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, true)", botId, context.User.ID)
						err := context.Postgres.QueryRow(context.Context, "SELECT owner FROM bot_owner WHERE bot_id = $1 AND main = true", botId).Scan(&owner)

						if err != nil {
							return err.Error()
						}

						return "This bot does not have a main owner. You have temporarily been given main owner as a result"
					}
				}

				log.Warn("Bot owner: ", owner.Int)

				context.Owner = strconv.FormatInt(owner.Int, 10)
				context.BotState = types.GetBotState(int(state.Int))

				var botMember *discordgo.Member
				var bot *discordgo.User
				var errm error

				botMember, errm = common.DiscordMain.State.Member(common.MainServer, botId)

				if errm != nil {
					bot = botMember.User
				} else {
					bot, errm = common.DiscordMain.User(botId)
					if errm != nil {
						return "This bot could not be found anywhere..."
					}
				}

				context.Bot = bot

				if context.Reason == "" && !adminOp.SlashRaw {
					context.Reason = "No reason specified"
				}

				opRes := adminOp.Handler(context)

				if (opRes == "" || strings.HasPrefix(opRes, "OK.")) && adminOp.Event != types.EventNone {
					eventId := common.CreateUUID()
					event := map[string]interface{}{
						"ctx": map[string]interface{}{
							"user":   context.User.ID,
							"reason": &context.Reason,
						},
						"m": map[string]interface{}{
							"event": adminOp.Event,
							"user":  context.User.ID,
							"ts":    float64(time.Now().Second()),
							"eid":   eventId,
							"t":     -1,
						},
					}

					// Add event
					var err error
					_, err = context.Postgres.Exec(context.Context, "INSERT INTO bot_api_event (bot_id, event, type, context, id) VALUES ($1, $2, $3, $4, $5)", botId, adminOp.Event, -1, event, eventId)

					if err != nil {
						log.Warning(err)
					}
					go common.AddWsEvent(context.Context, context.Redis, "bot-"+context.Bot.ID, eventId, event)
				}

				if !adminOp.SlashRaw {
					if opRes != "" {
						opRes += "\nState On Run: " + context.BotState.Str() + "\nBot owner: " + context.Owner
					} else {
						opRes = "OK."
					}
				}

				return opRes
			},
		}
	}
	return commandsToRet
}
