package serverlist

/*

Archived for future

import (
	"context"
	"encoding/json"
	"flamepaw/common"
	"flamepaw/slashbot"
	"flamepaw/types"
	"io/ioutil"
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/Fates-List/discordgo"
	"github.com/davecgh/go-spew/spew"
	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

const good = 0x00ff00
const bad = 0xe74c3c

var (
	commands      = make(map[string]ServerListCommand)
	commandsCache = make(map[string]string)
	numericRegex  *regexp.Regexp
	sanityRegex   *regexp.Regexp
)

func elementInSlice[T comparable](slice []T, elem T) bool {
	for i := range slice {
		if slice[i] == elem {
			return true
		}
	}
	return false
}

func init() {
	var err error
	var err2 error
	numericRegex, err = regexp.Compile("[^0-9]+")
	sanityRegex, err2 = regexp.Compile("[^a-zA-Z0-9]+")
	if err != nil {
		panic(err.Error())
	} else if err2 != nil {
		panic(err2.Error())
	}
}

// Admin OP Getter
func CmdInit() map[string]types.SlashCommand {
	commands["HELP"] = ServerListCommand{
		InternalName: "help",
		Perm:         1,
		Description:  "More information on how to use Fates List Server Listing",
		SlashOptions: []*discordgo.ApplicationCommandOption{},
		Handler: func(context types.SlashContext) string {
			return "Please see https://lynx.fateslist.xyz/docs/server-list for documentation on how to use Fates List Server Listing"
		},
	}

	commands["ALLOWLIST"] = ServerListCommand{
		InternalName: "allowlist",
		Description:  "Modifies the servers allowlist",
		Perm:         3,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "field",
				Description: "The list to modify",
				Choices: []*discordgo.ApplicationCommandOptionChoice{
					{
						Name:  "Whitelist",
						Value: "user_whitelist",
					},
					{
						Name:  "Blacklist",
						Value: "user_blacklist",
					},
				},
				Required: true,
			},
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "action",
				Description: "What to do on the allowlist",
				Choices: []*discordgo.ApplicationCommandOptionChoice{
					{
						Name:  "Add User",
						Value: "add_user",
					},
					{
						Name:  "Remove User",
						Value: "remove_user",
					},
					{
						Name:  "Clear",
						Value: "clear",
					},
				},
				Required: true,
			},
			{
				Type:        discordgo.ApplicationCommandOptionUser,
				Name:        "user",
				Description: "The user to add/remove. Can be a mention as well",
			},
		},
		Handler: func(context types.SlashContext) string {
			if context.Interaction.Token == "prefixCmd" {
				return "This is a slash command only command"
			}
			fieldVal := slashbot.GetArg(common.DiscordServerList, context.Interaction, "field", false)
			field, ok := fieldVal.(string)
			if !ok {
				return "Field must be provided"
			}
			actionVal := slashbot.GetArg(common.DiscordServerList, context.Interaction, "action", false)
			action, ok := actionVal.(string)
			if !ok {
				return "Action must be provided"
			}
			userVal := slashbot.GetArg(common.DiscordServerList, context.Interaction, "user", false)
			user, ok := userVal.(*discordgo.User)
			if !ok {
				user = &discordgo.User{ID: "0"}
			}

			guild, err := common.DiscordServerList.State.Guild(context.Interaction.GuildID)

			if err != nil {
				return dbError(err)
			}

			if err := auditLogUpdate(context, "allowlist:"+field+":"+action, "user="+user.ID, guild); err != "" {
				return err
			}

			if action == "clear" {
				_, err := context.Postgres.Exec(context.Context, "UPDATE servers SET "+field+" = $1 WHERE guild_id = $2", []string{}, context.Interaction.GuildID)
				if err != nil {
					return dbError(err)
				}
				return "Cleared " + field + " successfully!"
			} else if action == "add_user" {
				if user.ID == "0" {
					return "A `user` must be specified to perform this action"
				}

				var check pgtype.TextArray
				context.Postgres.QueryRow(context.Context, "SELECT "+field+" FROM servers WHERE guild_id = $1", context.Interaction.GuildID).Scan(&check)
				if check.Status == pgtype.Present && len(check.Elements) > 0 {
					if elementInSlice(check.Elements, pgtype.Text{Status: pgtype.Present, String: user.ID}) {
						return "This user is already on " + field
					}
				}

				_, err := context.Postgres.Exec(context.Context, "UPDATE servers SET "+field+" = "+field+" || $1 WHERE guild_id = $2", []string{user.ID}, context.Interaction.GuildID)
				if err != nil {
					return dbError(err)
				}
				return "Added " + user.Mention() + " to " + field + " successfully!"
			} else if action == "remove_user" {
				var check pgtype.TextArray
				context.Postgres.QueryRow(context.Context, "SELECT "+field+" FROM servers WHERE guild_id = $1", context.Interaction.GuildID).Scan(&check)
				if check.Status != pgtype.Present || len(check.Elements) <= 0 {
					return "No such user exists on " + field
				}

				var userFound bool
				var users []string
				for _, userElem := range check.Elements {
					if userElem.String != user.ID {
						users = append(users, userElem.String)
					} else {
						userFound = true
					}
				}

				if !userFound {
					return "No such user exists on " + field
				}

				_, err := context.Postgres.Exec(context.Context, "UPDATE servers SET "+field+" = $1 WHERE guild_id = $2", users, context.Interaction.GuildID)
				if err != nil {
					return dbError(err)
				}
				return "Removed " + user.Mention() + " from " + field
			}

			return "Work in progress, coming really soon!"
		},
	}
}

func GetCommandSpew() string {
	return spew.Sdump(commands)
}

*/
