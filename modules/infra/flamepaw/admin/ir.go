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

type irModalData struct {
	context types.SlashContext
	adminOp AdminOp
	botId   string
}

var contexts map[string]irModalData = make(map[string]irModalData)

func slashIr() map[string]types.SlashCommand {
	// Add the slash commands IR for use in slashbot. Is used internally by CmdInit

	slashbot.AddModalHandler("admin-ir", FinalHandler)

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
		for key, handler := range v.ModalResponses {
			slashbot.AddModalHandler(key, handler)
		}
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
					return "This admin operation does not exist (" + op + ")."
				}

				if adminOp.Server != "" && context.Interaction.GuildID != adminOp.Server {
					return "This command can only be run on server with id: " + adminOp.Server
				}

				context.ActionTargetType = types.ActionTargetTypeBot

				botVal := slashbot.GetArg(common.DiscordMain, context.Interaction, "bot", false)

				botId, ok := botVal.(string)

				if !ok && !adminOp.SlashRaw {
					botUser, ok := botVal.(*discordgo.User)
					if !ok {
						serverVal := slashbot.GetArg(common.DiscordMain, context.Interaction, "server", false)
						botId, ok = serverVal.(string)
						if !ok {
							return "No Bot Or Server ID provided"
						} else {
							if !adminOp.SupportsGuilds {
								return "This command does not support guilds right now / *yet*"
							}
							context.ActionTargetType = types.ActionTargetTypeServer
						}
					}
					botId = botUser.ID
				}

				if context.MockMode {
					return "Please exit mock mode and try again!"
				}

				if !adminOp.Critical {
					var verifyCode pgtype.Text
					context.Postgres.QueryRow(context.Context, "SELECT staff_verify_code FROM users WHERE user_id = $1", context.User.ID).Scan(&verifyCode)
					if verifyCode.Status != pgtype.Present || verifyCode.String != common.VerificationCode(context.User.ID) {
						return "You must verify in the staff server again to ensure you are up to date with our rules and staff guide"
					}
				}

				if context.StaffPerm < adminOp.MinimumPerm {
					return "This operation requires perm: " + strconv.Itoa(int(adminOp.MinimumPerm)) + " but you only have perm number " + strconv.Itoa(int(context.StaffPerm)) + ".\nUser ID: " + context.User.ID
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

					log.Warn("Bot owner: ", owner.Int)

					context.Owner = strconv.FormatInt(owner.Int, 10)
					context.BotState = types.GetBotState(int(state.Int))

					var botMember *discordgo.Member
					var bot *discordgo.User
					var errm error

					botMember, errm = common.DiscordMain.State.Member(common.MainServer, botId)

					if errm == nil {
						bot = botMember.User
					} else {
						bot, errm = common.DiscordMain.User(botId)
						if errm != nil {
							return "This bot could not be found anywhere..."
						}
					}

					context.Bot = bot
				}

				if !adminOp.SlashRaw {
					id := common.RandString(64)
					contexts[id] = irModalData{
						context: context,
						adminOp: adminOp,
						botId:   botId,
					}

					var reason string
					if len(adminOp.ModalReasonPlaceholder) > 0 {
						reason = "Reason"
					} else {
						reason = "Reason for this action"
					}

					modal := []discordgo.MessageComponent{
						discordgo.ActionsRow{
							Components: []discordgo.MessageComponent{
								discordgo.TextInput{
									CustomID:    "reason",
									Label:       "Reason",
									Style:       discordgo.TextInputStyleParagraph,
									Placeholder: reason,
									Required:    true,
									MinLength:   3,
									MaxLength:   1024,
								},
							},
						},
					}

					if len(adminOp.ExtraModals) > 0 {
						modal = append(modal, adminOp.ExtraModals...)
					}

					err := slashbot.SendModal(
						common.DiscordMain,
						context.Interaction,
						"Admin Operation",
						"admin-ir",
						id,
						modal,
					)
					log.Error(err)
				} else {
					return adminOp.Handler(context)
				}
				return "See modal, if you can't see it, upgrade your discord client"
			},
		}
	}
	return commandsToRet
}

func FinalHandler(modalCtx types.SlashContext) string {
	reasonVal := slashbot.GetArg(common.DiscordMain, modalCtx.Interaction, "reason", true)
	reason, ok := reasonVal.(string)

	if !ok {
		return "No reason specified!"
	}

	irModalDat, ok := contexts[modalCtx.ModalContext]

	if !ok {
		return "No modal data found!"
	}

	context := irModalDat.context
	adminOp := irModalDat.adminOp
	botId := irModalDat.botId

	context.Reason = reason
	context.ModalInteraction = modalCtx.Interaction

	opRes := adminOp.Handler(context)

	if !adminOp.SlashRaw && (opRes == "" || strings.HasPrefix(opRes, "OK.")) && adminOp.Event != types.EventNone {
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
}
