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

func tagCheck(tag string) bool {
	allowed := `abcdefghijklmnopqrstuvwxyz `
	nonCharacter := func(c rune) bool { return !strings.ContainsAny(allowed, strings.ToLower(string(c))) }
	words := strings.FieldsFunc(tag, nonCharacter)
	return tag == strings.Join(words, "")
}

func auditLogUpdate(context types.SlashContext, field string, value string, guild *discordgo.Guild) string {
	// Update server audit log here
	var auditVal string
	if len(value) > 30 {
		auditVal = value[:30] + "..."
	} else {
		auditVal = value
	}

	auditLogAction := map[string]interface{}{
		"user_id":    context.Interaction.Member.User.ID,
		"username":   context.Interaction.Member.User.Username,
		"user_perms": context.Interaction.Member.Permissions,
		"action_id":  common.CreateUUID(),
		"field":      field,
		"value":      auditVal,
		"ts":         float64(time.Now().Unix()) + 0.001, // Make sure its a float by adding 0.001
	}

	auditLogActionBytes, err := json.Marshal(auditLogAction)

	if err != nil {
		return dbError(err)
	}

	_, err = context.Postgres.Exec(context.Context, "UPDATE servers SET audit_logs = audit_logs || $1 WHERE guild_id = $2", []string{string(auditLogActionBytes)}, guild.ID)

	if err != nil {
		return dbError(err)
	}
	return ""
}

func dbError(err error) string {
	return "An error occurred while we were updating our database: " + err.Error()
}

func AddRecacheGuild(context context.Context, postgres *pgxpool.Pool, guild *discordgo.Guild) string {
	// Adds or recaches a guild
	if guild == nil {
		return "Guild cannot be nil"
	}

	var check pgtype.Int8
	postgres.QueryRow(context, "SELECT guild_id FROM servers WHERE guild_id = $1", guild.ID).Scan(&check)

	var nsfw bool
	if guild.NSFWLevel == discordgo.GuildNSFWLevelExplicit || guild.NSFWLevel == discordgo.GuildNSFWLevelAgeRestricted {
		nsfw = true
	}

	var memberCount int
	if guild.MemberCount > guild.ApproximateMemberCount {
		memberCount = guild.MemberCount
	} else {
		memberCount = guild.ApproximateMemberCount
	}

	var err error
	if check.Status != pgtype.Present {
		apiToken := common.RandString(198)
		_, err = postgres.Exec(context, "INSERT INTO servers (guild_id, guild_count, api_token, name_cached, avatar_cached, nsfw, owner_id) VALUES ($1, $2, $3, $4, $5, $6, $7)", guild.ID, memberCount, apiToken, guild.Name, guild.IconURL(), nsfw, guild.OwnerID)
		if err != nil {
			return dbError(err)
		}
	} else {
		_, err = postgres.Exec(context, "UPDATE servers SET name_cached = $1, avatar_cached = $2, nsfw = $3, guild_count = $4 WHERE guild_id = $5", guild.Name, guild.IconURL(), nsfw, guild.MemberCount, guild.ID)
		if err != nil {
			return dbError(err)
		}
	}
	return ""
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
	// Set sets a field
	commands["SET"] = ServerListCommand{
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
						Name:  "Invite Code",
						Value: "invite_url",
					},
					{
						Name:  "Invite Channel ID",
						Value: "invite_channel",
					},
					{
						Name:  "Website",
						Value: "website",
					},
					{
						Name:  "CSS",
						Value: "css",
					},
					{
						Name:  "Banner (Server Card)",
						Value: "banner_card",
					},
					{
						Name:  "Banner (Server Page)",
						Value: "banner_page",
					},
					{
						Name:  "Keep Banner Decorations",
						Value: "keep_banner_decor",
					},
					{
						Name:  "State",
						Value: "state",
					},
					{
						Name:  "Recache/Update Server Now",
						Value: "recache",
					},
					{
						Name:  "Vanity",
						Value: "vanity",
					},
					{
						Name:  "Webhook Secret",
						Value: "webhook_secret",
					},
					{
						Name:  "Webhook URL",
						Value: "webhook",
					},
					{
						Name:  "Webhook Type",
						Value: "webhook_type",
					},
					{
						Name:  "Requires Login",
						Value: "login_required",
					},
					{
						Name:  "Vote Roles",
						Value: "autorole_votes",
					},
					{
						Name:  "Whitelist Only",
						Value: "whitelist_only",
					},
					{
						Name:  "Whitelist Form",
						Value: "whitelist_form",
					},
				},
				Required: true,
			},
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "value",
				Description: "The value to set. Use 'none' to unset a field",
				Required:    true,
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
			valueVal := slashbot.GetArg(common.DiscordServerList, context.Interaction, "value", true)
			value, ok := valueVal.(string)
			if !ok || value == "" || value == "none" {
				if field == "recache" || field == "invite_url" || field == "invite_channel" || field == "banner_card" || field == "banner_page" || field == "webhook" || field == "website" || field == "autorole_votes" {
					value = ""
				} else {
					return "A value must be provided for this field"
				}
			}

			if field == "webhook_type" {
				if value != "0" && value != "1" {
					return "Webhook type must be 0 (vote) or 1 (discord integration, doesn't work yet)."
				}
			}

			value = strings.Replace(value, "http://", "https://", -1)
			value = strings.Replace(value, "www.", "https://www.", -1)

			// Handle state
			if field == "state" {
				if value == "private_viewable" || value == "8" {
					value = "8"
				} else if value == "public" || value == "0" {
					value = "0"
				} else {
					if context.StaffPerm > 4 {
						return "State must be one of (private_viewable, public)"
					} else {
						if _, err := strconv.Atoi(value); err != nil {
							return "State must be a number!"
						}
					}
				}

				var currState pgtype.Int4
				err := context.Postgres.QueryRow(context.Context, "SELECT state FROM servers WHERE guild_id = $1", context.Interaction.GuildID).Scan(&currState)
				if err != nil {
					return err.Error()
				}
				if currState.Status != pgtype.Present {
					return "An error has occurred fetching your current status"
				}
				state := types.GetBotState(int(currState.Int))

				if state != types.BotStateApproved && state != types.BotStatePrivateViewable {
					if context.StaffPerm > 4 {
						return "You may not change the state of this server. Please contact Fates List Staff for more information"
					}
				}
			}

			// Handle webhook secret and url
			if (field == "webhook_secret" || field == "webhook") && context.ServerPerm < 3 {
				return slashbot.ServerPermsString(3, true)
			}

			if field == "long_description_type" {
				if value == "0" || value == "html" {
					value = "0"
				} else if value == "1" || value == "markdown_pymarkdown" {
					value = "1"
				} else if value == "2" || value == "markdown_marked" || value == "markdown" {
					value = "2"
				} else {
					return "Long Description Type must be one of (html, markdown_pymarkdown, markdown_marked, markdown)"
				}
			}

			// Handle invite channel
			if field == "invite_channel" && value != "" {
				value = numericRegex.ReplaceAllString(value, "")
				_, err := common.DiscordServerList.State.Channel(value)
				if err != nil {
					return err.Error()
				}
			}

			// Handle keep banner decor
			if field == "keep_banner_decor" || field == "login_required" || field == "whitelist_only" {
				if value == "true" || value == "yes" {
					value = "true"
				} else if value == "false" || value == "no" {
					value = "false"
				} else {
					return "Value for this field must be one of (yes, no)"
				}
			}

			// Handle website
			if field == "whitelist_form" || field == "website" || field == "banner_card" || field == "banner_page" || field == "webhook" {
				if value != "" {
					if !strings.HasPrefix(value, "https://") {
						return "That is not a valid URL!"
					} else if strings.Contains(value, " ") {
						return "This field may not have spaces in the URL!"
					}
					if field == "banner_page" || field == "banner_card" {
						client := http.Client{Timeout: 5 * time.Second}
						var resp *http.Response
						var err error
						resp, err = client.Head(value)
						if err != nil || resp.StatusCode > 400 {
							resp, err = client.Get(value)
							if err != nil || resp.StatusCode > 400 {
								return "Could not resolve banner URL. Are you sure the URL works?"
							}
						}
						if !strings.HasPrefix(resp.Header.Get("Content-Type"), "image/") {
							return "This URL does not point to a valid image. Make sure the URL is valid and that there are no typos?"
						}
					}
				}
			}

			// Handle invite url
			if field == "invite_url" && value != "" {
				if !strings.HasPrefix(value, "https://") {
					value = "https://discord.gg/" + value
				}
				client := http.Client{Timeout: 5 * time.Second}
				resp, err := client.Get(value)
				if err != nil {
					return "Could not resolve invite, possibly invalid?"
				}
				value = resp.Request.URL.String()
				codeLst := strings.Split(value, "/")
				value = codeLst[len(codeLst)-1]
				if value == "" {
					return "Invalid invite provided"
				}
				invites, err := common.DiscordServerList.GuildInvites(context.Interaction.GuildID)
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

			guild, err := common.DiscordServerList.State.Guild(context.Interaction.GuildID)
			if err != nil {
				return "Could not find guild because: " + err.Error()
			}

			dbErr := AddRecacheGuild(context.Context, context.Postgres, guild)
			if dbErr != "" {
				return dbErr
			}

			if field != "recache" && field != "vanity" && field != "autorole_votes" {
				context.Postgres.Exec(context.Context, "UPDATE servers SET "+field+" = $1 WHERE guild_id = $2", value, context.Interaction.GuildID)
			} else if field == "vanity" {
				value = strings.ToLower(strings.Replace(value, " ", "", -1))
				var check pgtype.Text
				context.Postgres.QueryRow(context.Context, "SELECT DISTINCT vanity_url FROM vanity WHERE lower(vanity_url) = $1 AND redirect != $2", value, guild.ID).Scan(&check)
				if check.Status == pgtype.Present {
					return "This vanity is currently in use"
				} else if strings.Contains(value, "/") {
					return "This vanity is not allowed"
				}
				_, err := context.Postgres.Exec(context.Context, "DELETE FROM vanity WHERE redirect = $1", guild.ID)
				if err != nil {
					return "An error occurred while we were updating our database: " + err.Error()
				}
				_, err = context.Postgres.Exec(context.Context, "INSERT INTO vanity (type, vanity_url, redirect) VALUES ($1, $2, $3)", 0, value, guild.ID)
				if err != nil {
					return "An error occurred while we were updating our database: " + err.Error()
				}
			}

			// Handle vote roles and other autoroles here
			if field == "autorole_votes" {
				roleList := strings.Split(value, "|")
				validRoles := []string{}
				guildRoles, err := common.DiscordServerList.GuildRoles(context.Interaction.GuildID)

				if err != nil {
					return err.Error()
				}

				for _, grole := range guildRoles {
					for _, role := range roleList {
						if role == grole.ID {
							validRoles = append(validRoles, role)
						}
					}
				}

				if len(validRoles) == 0 && value != "" {
					return "No valid roles to autorole found!"
				}
				context.Postgres.Exec(context.Context, "UPDATE servers SET "+field+" = $1 WHERE guild_id = $2", validRoles, context.Interaction.GuildID)
			}

			// Update server audit log here
			if err := auditLogUpdate(context, field, value, guild); err != "" {
				return err
			}

			if field != "recache" {
				return "Successfully set " + field + "! Either see your servers page or use /get to verify that it got set to what you wanted!"
			}
			return "Recached server with " + strconv.Itoa(guild.MemberCount) + " members"
		},
	}

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
