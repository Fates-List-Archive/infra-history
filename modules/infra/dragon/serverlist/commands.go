package serverlist

import (
	"dragon/common"
	"dragon/types"
	"net/http"
	"strings"

	"github.com/bwmarrin/discordgo"
	"github.com/davecgh/go-spew/spew"
	"github.com/jackc/pgtype"
)

const good = 0x00ff00
const bad = 0xe74c3c

var (
	commands         = make(map[string]types.ServerListCommand)
	commandNameCache = make(map[string]string)
)

// Admin OP Getter
func cmdInit() {
	// Set sets a field
	commands["SET"] = types.ServerListCommand{
		InternalName: "set",
		Cooldown:     types.CooldownBucket{Name: "Update Bucket", InternalName: "update_bucket", Time: 5},
		Description:  "Sets a field, you may provide a pastebin link for long inputs",
		Perm:         2,
		Event:        types.EventNone,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "field",
				Description: "The field to update",
				Choices: []*discordgo.ApplicationCommandOptionChoice{
					{
						Name:  "Description",
						Value: "description",
					},
					{
						Name:  "Long Description",
						Value: "long_description",
					},
					{
						Name:  "Long Description Type",
						Value: "long_description_type",
					},
					{
						Name:  "Invite",
						Value: "invite_url",
					},
					{
						Name:  "Website",
						Value: "website",
					},
				},
				Required: true,
			},
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "value",
				Description: "The value to set",
				Required:    true,
			},
		},
		Handler: func(context types.ServerListContext) string {
			fieldVal := getArg(context.Discord, context.Interaction, "field", false)
			field, ok := fieldVal.(string)
			if !ok {
				return "Field must be provided"
			}
			valueVal := getArg(context.Discord, context.Interaction, "value", true)
			value, ok := valueVal.(string)
			if !ok {
				return "Value must be provided"
			}

			value = strings.Replace(value, "http://", "https://", -1)

			// Handle invite url
			if field == "invite_url" {
				if !strings.HasPrefix(value, "https://") {
					value = "https://discord.gg/" + value
				}
				resp, err := http.Get(value)
				if err != nil {
					return "Could not resolve invite, possibly invalid?"
				}
				value = resp.Request.URL.String()
				codeLst := strings.Split(value, "/")
				value = codeLst[len(codeLst)-1]
				if value == "" {
					return "Invalid invite provided"
				}
				invites, err := context.Discord.GuildInvites(context.Interaction.GuildID)
				if err != nil {
					return "Something went wrong!\nError: " + err.Error()
				}

				invite := common.InviteFilter(invites, value)

				if invite == nil {
					return "This invite does not exist on this server. Are you sure the specified invite is for this server?\nFound code: " + value
				}
				if invite.MaxUses != 0 {
					return "This is a limited-use invite"
				} else if invite.Revoked {
					return "This invite has been revoked?"
				} else if invite.MaxAge != 0 || invite.Temporary {
					return "This invite is only temporary. For optimal user experience, all invites must be unlimited time and use"
				} else {
					value = "https://discord.gg/" + invite.Code // Not needed per say, but useful for readability
				}
			}

			var check pgtype.Int8

			context.Postgres.QueryRow(context.Context, "SELECT guild_id FROM servers WHERE guild_id = $1", context.Interaction.GuildID).Scan(&check)

			if check.Status != pgtype.Present {
				guild, err := context.Discord.State.Guild(context.Interaction.GuildID)
				if err != nil {
					return "Could not add guild because: " + err.Error()
				}
				apiToken := common.RandString(198)
				_, err = context.Postgres.Exec(context.Context, "INSERT INTO servers (guild_id, api_token, name_cached) VALUES ($1, $2, $3)", context.Interaction.GuildID, apiToken, guild.Name)
				if err != nil {
					return "An error occurred while we were updating our database: " + err.Error()
				}
			}
			context.Postgres.Exec(context.Context, "UPDATE servers SET "+field+" = $1 WHERE guild_id = $2", value, context.Interaction.GuildID)
			return "Successfully set " + field + " to " + value + "!"
		},
	}
	// Load command name cache to map internal name to the command
	for cmdName, v := range commands {
		commandNameCache[v.InternalName] = cmdName
	}
}

func GetCommandSpew() string {
	return spew.Sdump("Admin commands loaded: ", commands)
}
