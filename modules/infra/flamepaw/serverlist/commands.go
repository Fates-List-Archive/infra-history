package serverlist

import (
	"context"
	"encoding/json"
	"flamepaw/common"
	"flamepaw/ipc"
	"flamepaw/slashbot"
	"flamepaw/types"
	"fmt"
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
	commands["GET"] = ServerListCommand{
		InternalName: "get",
		Description:  "Gets a field",
		Cooldown:     types.CooldownBucket{Name: "Get Bucket", InternalName: "get_bucket", Time: 5},
		Perm:         2,
		Event:        types.EventNone,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "field",
				Description: "Which field to get",
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
						Name:  "State",
						Value: "state",
					},
					{
						Name:  "NSFW Status",
						Value: "nsfw",
					},
					{
						Name:  "Website",
						Value: "website",
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
						Name:  "Banner (Server Card)",
						Value: "banner_card",
					},
					{
						Name:  "Banner (Server Page)",
						Value: "banner_page",
					},
					{
						Name:  "CSS",
						Value: "css",
					},
					{
						Name:  "Server API Token",
						Value: "api_token",
					},
					{
						Name:  "Webhook Secret",
						Value: "webhook_secret",
					},
					{
						Name:  "Vanity",
						Value: "vanity",
					},
					{
						Name:  "User Whitelist",
						Value: "user_whitelist",
					},
					{
						Name:  "User Blacklist",
						Value: "user_blacklist",
					},
					{
						Name:  "Audit Logs",
						Value: "audit_logs",
					},
					{
						Name:  "Requires Login",
						Value: "login_required",
					},
					{
						Name:  "Server Tags (ID form)",
						Value: "tags",
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
			if (field == "api_token" || field == "webhook_secret") && context.ServerPerm < 3 {
				return slashbot.ServerPermsString(3, true)
			}

			var v pgtype.Text

			if field == "vanity" {
				context.Postgres.QueryRow(context.Context, "SELECT vanity_url FROM vanity WHERE type = $1 AND redirect = $2", 0, context.Interaction.GuildID).Scan(&v)
			} else {
				context.Postgres.QueryRow(context.Context, "SELECT "+field+"::text FROM servers WHERE guild_id = $1", context.Interaction.GuildID).Scan(&v)
			}

			if v.Status != pgtype.Present {
				return field + " is not set!"
			}

			if field == "audit_logs" {
				var auditLogData []map[string]interface{}
				if len(v.String) > 3 {
					// Fix output for encoding/json since postgres gives a string'd json and not proper json output
					v.String = strings.Replace(strings.Replace(strings.Replace("["+v.String[2:len(v.String)-2]+"]", "\\", "", -1), "\"{", "{", -1), "}\"", "}", -1)
					err := json.Unmarshal([]byte(v.String), &auditLogData)
					if err != nil {
						return err.Error()
					}
					auditLogPretty, err := json.MarshalIndent(auditLogData, "", "    ")
					if err != nil {
						return err.Error()
					}
					v.String = string(auditLogPretty)
				}
			}

			if len(v.String) > 1994 {
				slashbot.SendIResponseEphemeral(common.DiscordServerList, context.Interaction, "Value of `"+field+"`", false, v.String)
			} else {
				slashbot.SendIResponseEphemeral(common.DiscordServerList, context.Interaction, "Value of "+field+"\n```"+v.String+"```", false)
			}
			return ""
		},
	}

	commands["VOTESERVER"] = ServerListCommand{
		InternalName: "voteserver",
		Description:  "Vote for this server!",
		Perm:         1,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionBoolean,
				Name:        "test",
				Description: "Whether or not to create a 'test' vote. This vote is not counted. This is Manage Server/Admin only",
			},
		},
		Handler: func(context types.SlashContext) string {
			log.Info("Running test")
			testVal := slashbot.GetArg(common.DiscordServerList, context.Interaction, "test", false)
			test, ok := testVal.(bool)
			if !ok {
				test = false
			}

			if test && context.ServerPerm < 3 {
				return slashbot.ServerPermsString(3, true)
			}

			key := "vote_lock+server:" + context.Interaction.Member.User.ID
			check := context.Redis.PTTL(context.Context, key).Val()
			debug := "**DEBUG (for nerds)**\nRedis TTL: " + strconv.FormatInt(check.Milliseconds(), 10) + "\nKey: " + key + "\nTest: " + strconv.FormatBool(test)
			var voteMsg string // The message that will be shown to the use on a successful vote

			if check.Milliseconds() == 0 || test {
				var userId string = context.Interaction.Member.User.ID
				if test {
					// TODO: Check if test votes are currently enabled. For now use perm 2
					if context.ServerPerm < 2 {
						return slashbot.ServerPermsString(2, true)
					}
				}

				var votesDb pgtype.Int8

				err := context.Postgres.QueryRow(context.Context, "SELECT votes FROM servers WHERE guild_id = $1", context.Interaction.GuildID).Scan(&votesDb)

				if err != nil {
					return dbError(err)
				}

				votes := votesDb.Int + 1

				eventId := common.CreateUUID()

				voteEvent := map[string]interface{}{
					"votes": votes,
					"id":    userId,
					"ctx": map[string]interface{}{
						"user":  userId,
						"votes": votes,
						"test":  test,
					},
					"m": map[string]interface{}{
						"e":    types.EventServerVote,
						"user": userId,
						"t":    -1,
						"ts":   float64(time.Now().Unix()) + 0.001, // Make sure its a float by adding 0.001
						"eid":  eventId,
					},
				}

				vote_b, err := json.Marshal(voteEvent)
				if err != nil {
					return dbError(err)
				}

				go func() {
					common.AddWsEvent(context.Context, context.Redis, "server-"+context.Interaction.GuildID, eventId, voteEvent)

					voteStr := string(vote_b)

					ok, webhookType, secret, webhookURL := common.GetWebhook(context.Context, "servers", context.Interaction.GuildID, context.Postgres)
					if !ok {
						voteMsg = "You have successfully voted for this server (note: this server does not support vote rewards if you were expecting a reward)"
					} else {
						voteMsg = "You have successfully voted for this server"
						common.WebhookReq(context.Context, context.Redis, context.Postgres, eventId, webhookURL, secret, voteStr, userId, context.Interaction.GuildID, 0)
						log.Debug("Got webhook type of " + strconv.Itoa(int(webhookType)))
					}
				}()

				// Handle vote autoroles
				var roles pgtype.Int8Array

				verr := context.Postgres.QueryRow(context.Context, "SELECT autorole_votes FROM servers WHERE guild_id = $1", context.Interaction.GuildID).Scan(&roles)

				if verr != nil {
					voteMsg += "\nVote role error: " + dbError(err)
				}

				if roles.Status == pgtype.Present {
					for _, role := range roles.Elements {
						roleID := strconv.FormatInt(role.Int, 10)
						err := common.DiscordServerList.GuildMemberRoleAddWithReason(context.Interaction.GuildID, userId, roleID, "Autorole for user "+userId)
						if err != nil {
							voteMsg += "\nVote role error when giving role " + roleID + ": " + err.Error()
						}
					}
				}

				if !test {
					context.Postgres.Exec(context.Context, "UPDATE servers SET votes = votes + 1, total_votes = total_votes + 1 WHERE guild_id = $1", context.Interaction.GuildID)
					context.Redis.Set(context.Context, key, 0, 8*time.Hour)
				}
			} else {
				hours := check / time.Hour
				mins := (check - (hours * time.Hour)) / time.Minute
				secs := (check - (hours*time.Hour + mins*time.Minute)) / time.Second
				voteMsg = fmt.Sprintf("Please wait %02d hours, %02d minutes %02d seconds", hours, mins, secs)
			}

			return voteMsg + "\n\n" + debug
		},
	}

	commands["BUMP"] = ServerListCommand{
		InternalName: "bump",
		Handler: func(context types.SlashContext) string {
			return commands["VOTE"].Handler(context)
		},
	}

	commands["HELP"] = ServerListCommand{
		InternalName: "help",
		Perm:         1,
		Description:  "More information on how to use Fates List Server Listing",
		SlashOptions: []*discordgo.ApplicationCommandOption{},
		Handler: func(context types.SlashContext) string {
			intro := "**Welcome to Fates List**\n" +
				"If you're reading this, you probably already know what server listing (and slash commands) are. This guide will not go over that"

			syntax := "**Slash command syntax**\n" +
				"This guide will use the following syntax for slash commands: `/command option:foo anotheroption:bar`. " +
				"To specify a list of values (where supported), use |. Currently only Vote Roles supports this"

			faqBasics := "**How do I add my server?**+\n" +
				"Good question. Your server should usually be automatically added for you once you add the bot to your server. " +
				"Just set a description using `/set field:descriotion value:My lovely description`. If you do not do so, the description " +
				"will be randomly set for you and it will likely not be what you want. You **should** set a long description using " +
				"`/set field:long_description value:My really really long description`. **For really long descriptions, you can also create " +
				"a paste on pastebin and provide the pastebin link as the value**"

			faqState := "**What is the 'State' option?**\n" +
				"Long story short, state allows you to configure the privacy of your server and in the future may do other things as well. " +
				"*What is this privacy, you ask?* Well, if you are being raided and you wish to stop people from joining your server during a " +
				"raid, then you can simply set the state of your server to `private_viewable` or `8`. This will stop it from being indexed " +
				"and will *also* block users from joining your server until you're ready to set the state to `public` or `0`."

			faqVoteRewards := "**Vote Rewards**\n" +
				"You can reward users for voting for your server using vote rewards. This can be things like custom roles or extra perks! " +
				"In order to use vote rewards, you will either need to get your API Token (or your Webhook Secret if you have one set and " +
				"wish to use webhooks) or you will need to use our websocket API to listen for events. Once you have gotten a server vote " +
				"event, you can then give rewards for voting. The event number for server votes is `71`"

			faqAllowlist := "**Server Allow List**\n" +
				"For invite-only servers, you can/should use a **user whitelist** to prevent users outside the user whitelist from " +
				"joining your server. If you do not have any users on your user whitelist, anyone may join your server. User blacklists allow " +
				"you to blacklist bad users from getting an invite to your server via Fates List. Use `/allowlist` to configure the allow list"

			faqTags := "**Server Tags**\n" +
				"Server Tags on Fates List are a great way to allow similar users to find your server! The first server to make a tag is given " +
				"ownership over that tag. **Tag owners can control the iconify emoji of the tag however they *cannot* remove the tag from their " +
				"server without transferring it to another server.** The Fates List Staff Server is the default server a tag will transfer to. " +
				"Tags should be compelling and quickly describe the server. **Creating a new similar tag just to gain ownership of it may result " +
				"in a ban**. Tags shoild also be short and **a maximum of 20 characters in length**. Some keywords are not allowed/reserved as " +
				"well"

			helpPages := []string{
				strings.Join([]string{intro, syntax, faqBasics, faqState}, "\n\n"),
				strings.Join([]string{faqVoteRewards, faqAllowlist, faqTags}, "\n\n"),
			}

			var sender func(discord *discordgo.Session, i *discordgo.Interaction, content string, clean bool, largeContent ...string)
			if context.Interaction.Token == "prefixCmd" {
				sender = slashbot.SendIResponse
			} else {
				sender = slashbot.SendIResponseEphemeral
			}

			for i, v := range helpPages {
				if i == 0 {
					sender(common.DiscordServerList, context.Interaction, "Start of message", false)
				}
				sender(common.DiscordServerList, context.Interaction, v, false)
			}
			return ""
		},
	}

	commands["TAGS"] = ServerListCommand{
		InternalName: "tags",
		Description:  "Modifies server tags. Use get for getting the server tags",
		Perm:         2,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "action",
				Description: "What do you want to do with the tags",
				Choices: []*discordgo.ApplicationCommandOptionChoice{
					{
						Name:  "Add Tag",
						Value: "add",
					},
					{
						Name:  "Remove Tag",
						Value: "remove",
					},
					{
						Name:  "Transfer Tag Ownership",
						Value: "transfer",
					},
					{
						Name:  "Set Tag Decoration",
						Value: "iconify_data",
					},
				},
				Required: true,
			},
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "tag",
				Description: "The tags name",
				Required:    true,
			},
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "transfer-server",
				Description: "The server ID to transfer a tag to. Only applies to transfers. Defaults to our staff server.",
			},
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "iconify-data",
				Description: "The 'iconify-data' you wish to set as decoration for your tag (https://iconify.design)",
			},
		},
		Handler: func(context types.SlashContext) string {
			if context.Interaction.Token == "prefixCmd" {
				return "This is a slash command only command"
			}
			actionVal := slashbot.GetArg(common.DiscordServerList, context.Interaction, "action", false)
			action, ok := actionVal.(string)
			if !ok {
				return "Action must be provided"
			}
			tagVal := slashbot.GetArg(common.DiscordServerList, context.Interaction, "tag", false)
			tag, ok := tagVal.(string)
			if !ok {
				return "Tag name must be provided"
			}

			if !tagCheck(tag) {
				return "This tag name is not allowed. Make sure you are only using letters and spaces"
			}

			tagNameInternal := strings.ToLower(strings.Replace(tag, " ", "-", -1))

			if len(tagNameInternal) > 20 {
				return "Tag names can only be a maximum of 20 characters long!"
			}

			bannedKws := []string{"best-", "good-", "fuck", "nigger", "fates-list", "fateslist"}

			for _, kw := range bannedKws {
				if strings.Contains(tagNameInternal, kw) {
					return "'" + kw + "' is not allowed in a tag"
				}
			}

			if action == "remove" {
				// Note that just removing a tag that you own is not allowed and such tags must be transferred
				var check pgtype.Text
				context.Postgres.QueryRow(context.Context, "SELECT owner_guild::text FROM server_tags WHERE id = $1", tagNameInternal).Scan(&check)
				if check.Status != pgtype.Present {
					return "This server tag does not even exist!"
				} else if check.String == context.Interaction.GuildID {
					if context.Interaction.GuildID != common.StaffServer {
						return "You cannot remove tags you own without first transferring them to a new server. See `/help` for more information on tag permissions."
					} else {
						tx, err := context.Postgres.Begin(context.Context)
						if err != nil {
							return dbError(err)
						}
						defer tx.Rollback(context.Context)
						_, err = tx.Exec(context.Context, "UPDATE servers SET tags = array_remove(tags, $1) WHERE tags && $2", tagNameInternal, []string{tagNameInternal})
						if err != nil {
							return dbError(err)
						}
						_, err = tx.Exec(context.Context, "DELETE FROM server_tags WHERE id = $1", tagNameInternal)
						if err != nil {
							return dbError(err)
						}
						err = tx.Commit(context.Context)
						if err != nil {
							return dbError(err)
						}

					}
				}

				_, err := context.Postgres.Exec(context.Context, "UPDATE servers SET tags = array_remove(tags, $1) WHERE guild_id = $2", tagNameInternal, context.Interaction.GuildID)
				if err != nil {
					return dbError(err)
				}
				return "Removed " + tagNameInternal + " from server tags"
			} else if action == "add" {
				var check pgtype.Text
				context.Postgres.QueryRow(context.Context, "SELECT owner_guild::text FROM server_tags WHERE id = $1", tagNameInternal).Scan(&check)
				if check.Status != pgtype.Present {
					_, err := context.Postgres.Exec(context.Context, "INSERT INTO server_tags (id, name, iconify_data, owner_guild) VALUES ($1, $2, $3, $4)", tagNameInternal, tag, "fluent:animal-cat-28-regular", context.Interaction.GuildID)
					if err != nil {
						return dbError(err)
					}
				}
				var tags pgtype.TextArray
				context.Postgres.QueryRow(context.Context, "SELECT tags FROM servers WHERE guild_id = $1", context.Interaction.GuildID).Scan(&tags)
				if tags.Status != pgtype.Present {
					return "Invalid tag configuration! Please ask for help on our support server!"
				} else if len(tags.Elements) > 5 {
					return "Servers may only have a maximum of 5 tags"
				}
				for _, tag := range tags.Elements {
					if tag.String == tagNameInternal {
						return "Your server already has this tag set/added!"
					}
				}
				_, err := context.Postgres.Exec(context.Context, "UPDATE servers SET tags = tags || $1 WHERE guild_id = $2", []string{tagNameInternal}, context.Interaction.GuildID)
				if err != nil {
					return dbError(err)
				}
				return "Tag " + tag + " successfully added"
			} else if action == "transfer" {
				var check pgtype.Text
				context.Postgres.QueryRow(context.Context, "SELECT owner_guild::text FROM server_tags WHERE id = $1", tagNameInternal).Scan(&check)
				if check.Status != pgtype.Present {
					return "This tag does not exist!"
				} else if check.String != context.Interaction.GuildID && context.Interaction.GuildID != common.StaffServer {
					return "You may not transfer the ownership of tags you do not own!"
				}

				transferServerVal := slashbot.GetArg(common.DiscordServerList, context.Interaction, "transfer-server", false)
				transferServer, ok := transferServerVal.(string)
				if !ok || transferServer == "" {
					return "You must specify a transfer server or say 'none' to transfer to staff server by default"
				} else if transferServer == "none" {
					transferServer = common.StaffServer
				}

				if transferServer != common.StaffServer {
					// Ensure the other server also has this tag set
					var check pgtype.TextArray
					err := context.Postgres.QueryRow(context.Context, "SELECT tags FROM servers WHERE guild_id = $1", transferServer).Scan(&check)
					if err != nil {
						return "Could not find the recipient server!"
					}
					var ok bool
					for _, tag := range check.Elements {
						if tag.String == tagNameInternal {
							ok = true
						}
					}
					if !ok {
						return "The recipient server does not also have this tag set and so cannot be transferred to"
					}
				}

				_, err := context.Postgres.Exec(context.Context, "UPDATE server_tags SET owner_guild = $1 WHERE id = $2", transferServer, tagNameInternal)
				if err != nil {
					return dbError(err)
				}
				return "Transferred ownership of " + tagNameInternal + " to " + transferServer + ". Please contact support if this was a mistake or if you wish to revert the transfer!"
			} else if action == "iconify_data" {
				var check pgtype.Text
				context.Postgres.QueryRow(context.Context, "SELECT owner_guild::text FROM server_tags WHERE id = $1", tagNameInternal).Scan(&check)
				if check.Status != pgtype.Present {
					return "This tag does not exist!"
				} else if check.String != context.Interaction.GuildID && context.Interaction.GuildID != common.StaffServer {
					return "You can't set the decoration for a tag you do not own!"
				}

				iconifyDataVal := slashbot.GetArg(common.DiscordServerList, context.Interaction, "iconify-data", false)
				iconifyData, ok := iconifyDataVal.(string)

				if !ok || iconifyData == "" {
					return "You must provide a value for the iconify-data option to decorate your tag. Set this to 'none' to disable decorations for your tag"
				} else if iconifyData == "none" {
					iconifyData = "fluent:animal-cat-28-regular"
				}

				illegalIconifyDataChars := []string{"<", ">", ";", "'", `"`, "&"}

				for _, v := range illegalIconifyDataChars {
					if strings.Contains(iconifyData, v) {
						return v + " is not a valid character. If your tags decoration does reauire this character or if this is an error, please contact Fates List Support!"
					}
				}

				_, err := context.Postgres.Exec(context.Context, "UPDATE server_tags SET iconify_data = $1 WHERE id = $2", iconifyData, tagNameInternal)
				if err != nil {
					return dbError(err)
				}
				return "Successfully changed the decoration for this tag to: " + iconifyData
			}

			return "Work in progress. Coming really soon though!"
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
					if ipc.ElementInSlice(check.Elements, pgtype.Text{Status: pgtype.Present, String: user.ID}) {
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

	// Load command name cache to map internal name to the command
	var commandsToRet map[string]types.SlashCommand = make(map[string]types.SlashCommand)
	for cmdName, v := range commands {
		commandsCache[v.InternalName] = cmdName
		commandsToRet[cmdName] = types.SlashCommand{
			CmdName:     cmdName,
			Name:        v.InternalName,
			Description: v.Description,
			Options:     v.SlashOptions,
			Cooldown:    v.Cooldown,
			Server:      v.Server,
			Handler: func(context types.SlashContext) string {
				// Prehandler that runs our server list handler
				var ok bool

				cmdName, ok := commandsCache[context.AppCmdData.Name]

				if !ok {
					return "Command " + context.AppCmdData.Name + " not found..."
				}

				v, ok := commands[cmdName]

				if !ok {
					return "Command " + context.AppCmdData.Name + " not found..."
				}

				log.Info(context.ServerPerm, v.Perm)

				if context.ServerPerm < v.Perm {
					return slashbot.ServerPermsString(v.Perm, true)
				}
				return v.Handler(context)
			},
		}
	}
	return commandsToRet
}

func GetCommandSpew() string {
	return spew.Sdump(commands)
}
