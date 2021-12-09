package admin

// ir.go handles the slash command IR and passes over the admin operation to silverpelt.go

import (
	"context"
	"dragon/common"
	"dragon/types"
	"strconv"

	"github.com/Fates-List/discordgo"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgx/v4/pgxpool"
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
	var commandsToRet map[string]types.SlashCommand = make(map[string]types.SlashCommand)
	for cmdName, v := range commands {
		if !v.SlashRaw {
			v.SlashOptions = Prepend(v.SlashOptions, &botIdOption)
		}

		commandsToRet[cmdName] = types.SlashCommand{
			Index:       cmdName,
			Name:        v.InternalName,
			Description: v.Description,
			Cooldown:    v.Cooldown,
			Options:     v.SlashOptions,
			Server:      v.Server,
			Handler: func(discord *discordgo.Session, postgres *pgxpool.Pool, redis *redis.Client, interaction *discordgo.Interaction, appCmdData discordgo.ApplicationCommandInteractionData, index string) string {
				return adminSlashHandler(context.Background(), discord, redis, postgres, interaction, commands[index], appCmdData)
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
	var extraContext string

	if op == "" {
		return ""
	}

	// Get required name of context field/the name of the argument that should be treated as context
	var slashContext string

	if cmd.SlashContextField == "" {
		slashContext = "context"
	} else {
		slashContext = cmd.SlashContextField
	}

	// Get needed interaction options using loop
	for _, v := range appCmdData.Options {
		if v.Name == "bot" {
			botId = v.UserValue(discord).ID
		} else if v.Name == "reason" {
			reason = common.RenderPossibleLink(v.StringValue())
		} else if v.Name == slashContext {
			if v.Type == discordgo.ApplicationCommandOptionString {
				extraContext = v.StringValue()
			} else if v.Type == discordgo.ApplicationCommandOptionInteger {
				extraContext = strconv.FormatInt(v.IntValue(), 10)
			}
		}
	}

	return silverpelt(
		ctx,
		discord,
		i,
		rdb,
		db,
		i.Member.User.ID,
		botId,
		op,
		types.AdminRedisContext{
			Reason:       reason,
			ExtraContext: &extraContext,
		},
		i.GuildID,
	)
}
