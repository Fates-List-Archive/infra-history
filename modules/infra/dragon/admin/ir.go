package admin

// ir.go handles the slash command IR and passes over the admin operation to silverpelt.go

import (
	"context"
	"dragon/common"
	"dragon/types"

	"github.com/Fates-List/discordgo"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgx/v4/pgxpool"
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
			Index:         cmdName,
			Name:          v.InternalName,
			Description:   v.Description,
			Cooldown:      v.Cooldown,
			Options:       v.SlashOptions,
			Server:        v.Server,
			Autocompleter: v.Autocompleter,
			Handler: func(handler types.HandlerData) string {
				return adminSlashHandler(handler.Context, handler.Discord, handler.Redis, handler.Postgres, handler.Interaction, commands[handler.Index], handler.AppCmdData)
			},
		}
	}
	return commandsToRet
}

func adminSlashHandler(
	ctx context.Context,
	discord *discordgo.Session,
	rdb *redis.Client,
	db *pgxpool.Pool,
	i *discordgo.Interaction,
	cmd types.AdminOp,
	appCmdData discordgo.ApplicationCommandInteractionData,
) string {
	var botId string
	var op string = commandNameCache[appCmdData.Name]
	var reason string

	if op == "" {
		return ""
	}

	// Get needed interaction options using loop
	for _, v := range appCmdData.Options {
		if v.Name == "bot" {
			if v.Type == discordgo.ApplicationCommandOptionString {
				botId = v.StringValue()
			} else {
				botId = v.UserValue(discord).ID
			}
		} else if v.Name == "reason" {
			reason = common.RenderPossibleLink(v.StringValue())
		}
	}

	return SilverpeltCmdHandle(
		ctx,
		discord,
		i,
		rdb,
		db,
		i.Member.User.ID,
		botId,
		op,
		types.AdminRedisContext{
			Reason: reason,
		},
		i.GuildID,
	)
}
