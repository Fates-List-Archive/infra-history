package supportsystem

import (
	"context"
	"flamepaw/common"
	"flamepaw/slashbot"
	"flamepaw/types"
	"fmt"
	"strings"
	"time"

	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"

	"github.com/Fates-List/discordgo"
)

var rolesMsg *discordgo.Message
var rolesMenu = []discordgo.MessageComponent{
	discordgo.ActionsRow{
		Components: []discordgo.MessageComponent{
			discordgo.SelectMenu{
				CustomID:    "roles",
				Placeholder: "Choose your roles!",
				MaxValues:   3,
				Options: []discordgo.SelectMenuOption{
					{
						Label:       "I Love Pings",
						Value:       "ilovepings",
						Description: "I love being pinged!",
						Emoji: discordgo.ComponentEmoji{
							Name: "🏓",
						},
					},
					{
						Label:       "News Ping",
						Value:       "news",
						Description: "I want the important news!",
						Emoji: discordgo.ComponentEmoji{
							Name: "📰",
						},
					},
					{
						Label:       "Add Bot Ping",
						Value:       "addbot",
						Description: "I want to see every new bot! Required by all bot reviewers",
						Emoji: discordgo.ComponentEmoji{
							Name: "🤖",
						},
					},
					{
						Label:       "Giveaway Ping",
						Value:       "giveaway",
						Description: "I want to be pinged for giveaways!",
						Emoji: discordgo.ComponentEmoji{
							Name: "🎉",
						},
					},
				},
			},
		},
	},
}

// Returns true if added, false if removed
func giveRole(id string, m *discordgo.Member, onlyGive bool) bool {
	// Yes, I know this is a terrible way to do this, but I'm ~not sure~ too lazy to do it better
	var rolesMap = map[string]string{
		"ilovepings": common.ILovePingsRole,
		"news":       common.NewsPingRole,
		"addbot":     common.StaffPingAddRole,
		"giveaway":   common.GiveawayPingRole,
		"certified":  common.CertifiedDevRole, // only accessible to certified users
		"botdev":     common.BotDevRole,       // only accessible to bot devs
	}

	roleID, ok := rolesMap[id]
	if !ok {
		return false // No role found
	}

	if onlyGive {
		common.DiscordMain.GuildMemberRoleAdd(common.MainServer, m.User.ID, roleID)
		return true
	}

	var hasRole bool
	for _, role := range m.Roles {
		if role == roleID {
			hasRole = true
		}
	}

	if !hasRole {
		// Add role
		common.DiscordMain.GuildMemberRoleAdd(common.MainServer, m.User.ID, roleID)
		return true
	} else {
		// Remove role
		common.DiscordMain.GuildMemberRoleRemove(common.MainServer, m.User.ID, roleID)
		return false
	}
}

var msgSendTries = 0

func SendRolesMessage(s *discordgo.Session, m *discordgo.Ready) {
	msgs, err := s.ChannelMessages(common.RolesChannel, 100, "", "", "")

	if err != nil {
		log.Error(err)
	}

	for _, msg := range msgs {
		if msg.Author.ID == s.State.User.ID {
			s.ChannelMessageDelete(common.RolesChannel, msg.ID)
		}
	}

	rolesMsg, err = s.ChannelMessageSendComplex(common.RolesChannel, &discordgo.MessageSend{
		Embeds: []*discordgo.MessageEmbed{
			{
				Title:       "Fates List Roles",
				Description: "Hey there 👋! Please grab your roles here. Use the below 'Get Old Roles' for Bot/Certified Developer roles!",
			},
		},
		Components: rolesMenu,
	})

	if err != nil {
		panic(err)
	}

	s.ChannelMessageSendComplex(common.RolesChannel, &discordgo.MessageSend{
		Content: "If you have the Bronze User role, you can redeem it for a free upvote every 24 hours here!",
		Components: []discordgo.MessageComponent{
			discordgo.ActionsRow{
				Components: []discordgo.MessageComponent{
					discordgo.Button{
						CustomID: "bronze-redeem",
						Label:    "Redeem Daily Reward",
					},
				},
			},
		},
	})

	s.ChannelMessageSendComplex(common.RolesChannel, &discordgo.MessageSend{
		Content: "Click the button below to get the Bot/Certified Developer roles if you don't already have it!",
		Components: []discordgo.MessageComponent{
			discordgo.ActionsRow{
				Components: []discordgo.MessageComponent{
					discordgo.Button{
						CustomID: "get-old-roles",
						Label:    "Get Old Roles",
					},
				},
			},
		},
	})
}

func MessageHandler(
	ctx context.Context,
	discord *discordgo.Session,
	rdb *redis.Client,
	db *pgxpool.Pool,
	i *discordgo.Interaction,
) {
	data := i.MessageComponentData()
	if data.CustomID == "roles" {
		givenRoles := []string{}
		takenRoles := []string{}
		for _, role := range data.Values {
			ok := giveRole(role, i.Member, false)
			if ok {
				givenRoles = append(givenRoles, role)
			} else {
				takenRoles = append(takenRoles, role)
			}
		}
		common.DiscordMain.ChannelMessageEditComplex(&discordgo.MessageEdit{
			ID:         rolesMsg.ID,
			Channel:    rolesMsg.ChannelID,
			Components: rolesMenu,
		})
		var msg = ""
		if len(givenRoles) > 0 {
			msg = fmt.Sprintf("You have been given the following roles: %s\n", strings.Join(givenRoles, " | "))
		}
		if len(takenRoles) > 0 {
			msg += fmt.Sprintf("You have been removed from the following roles: %s\n", strings.Join(takenRoles, " | "))
		}
		msg += "**If you see a bug here, please report it!**"
		slashbot.SendIResponseEphemeral(common.DiscordMain, i, msg, false)
		return
	} else if data.CustomID == "bronze-redeem" {
		var bronzeUser bool
		for _, role := range i.Member.Roles {
			if role == common.BronzeUserRole {
				bronzeUser = true
			}
		}

		if !bronzeUser {
			slashbot.SendIResponseEphemeral(common.DiscordMain, i, "You may not redeem this reward", false)
			return
		}

		check := rdb.Exists(ctx, "redeem:"+i.Member.User.ID).Val()
		if check != 0 {
			slashbot.SendIResponseEphemeral(common.DiscordMain, i, "You have already redeemed your daily reward!", false)
			return
		}

		voteCheck := rdb.Exists(ctx, "vote_lock:"+i.Member.User.ID).Val()
		if voteCheck != 0 {
			slashbot.SendIResponseEphemeral(common.DiscordMain, i, "You have not yet voted for a bot on Fates List in the last 8 hours!", false)
		}

		rdb.Del(ctx, "vote_lock:"+i.Member.User.ID)
		rdb.Set(ctx, "redeem:"+i.Member.User.ID, "1", time.Hour*24)
		slashbot.SendIResponseEphemeral(common.DiscordMain, i, "You have redeemed your daily free upvote successfully", false)
	} else if data.CustomID == "get-old-roles" {
		bots, err := db.Query(ctx, "SELECT bots.bot_id::text, bots.state FROM bots INNER JOIN bot_owner ON bot_owner.bot_id = bots.bot_id WHERE bot_owner.owner = $1", i.Member.User.ID)
		if err != nil {
			slashbot.SendIResponseEphemeral(common.DiscordMain, i, err.Error(), false)
			return
		}
		defer bots.Close()

		var botDev bool
		var botDevBots []string
		var certDevBots []string
		var certDev bool

		for bots.Next() {
			if botDev && certDev {
				break
			}
			var botID pgtype.Text
			var state pgtype.Int4
			err := bots.Scan(&botID, &state)
			if err != nil {
				slashbot.SendIResponseEphemeral(common.DiscordMain, i, err.Error(), false)
				return
			}

			if types.GetBotState(int(state.Int)) == types.BotStateCertified {
				certDev = true
				certDevBots = append(certDevBots, botID.String)
				giveRole("certified", i.Member, true)
			} else if types.GetBotState(int(state.Int)) == types.BotStateApproved {
				botDev = true
				botDevBots = append(botDevBots, botID.String)
				giveRole("botdev", i.Member, true)
			}
		}
		slashbot.SendIResponseEphemeral(common.DiscordMain, i, fmt.Sprintf("**Roles gotten**\nBot developer: %t (%v)\nCertified developer: %t (%v)", botDev, botDevBots, certDev, certDevBots), false)
	}
}
