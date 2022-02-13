package supportsystem

import (
	"context"
	"encoding/json"
	"flamepaw/common"
	"flamepaw/slashbot"
	"flamepaw/types"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"

	"github.com/Fates-List/discordgo"
)

type staffAppPages struct {
	Title     string     `json:"title"`
	Pre       string     `json:"pre"`
	Questions []staffApp `json:"questions"`
}

type staffApp struct {
	ID        string `json:"id"`
	Title     string `json:"title"`
	Question  string `json:"question"`
	MinLength int    `json:"min_length"`
	MaxLength int    `json:"max_length"`
	Paragraph bool   `json:"paragraph"`
}

var baypawApps = map[string]map[string]interface{}{}

var staffAppQuestions = []staffAppPages{
	{
		Title: "Basics",
		Questions: []staffApp{
			{
				ID:        "tz",
				Title:     "Time Zone",
				Question:  "Please enter your timezone (the 3 letter code).",
				MinLength: 3,
				MaxLength: 3,
			},
			{
				ID:        "age",
				Title:     "Age (14+ only!)",
				Question:  "What is your age? Will be investigated",
				MinLength: 2,
				MaxLength: 2,
			},
			{
				ID:        "lang",
				Title:     "Languages",
				Question:  "What languages do you know?",
				MinLength: 10,
				MaxLength: 100,
			},
			{
				ID:        "history",
				Title:     "History",
				Question:  "Have you ever been demoted due to inactivity? If so, why?",
				MinLength: 10,
				MaxLength: 100,
			},
			{
				ID:        "why",
				Title:     "Motivation",
				Question:  "Why do you want to be a bot reviewer and how much experience do you have?",
				Paragraph: true,
				MinLength: 30,
				MaxLength: 4000,
			},
		},
	},
	{
		Title: "Personality",
		Pre:   "This section is just to see how well you can communicate with other people and argue with completely random points. You will need to use Google here. If you dont understand something, look up each name on the internet",
		Questions: []staffApp{
			{
				ID:        "sumcat",
				Title:     "Summarize",
				Question:  "Summarize the life on one cat from: Mistystar, Graystripe, Frostpaw, Flamepaw or Sunbeam?",
				MinLength: 10,
				MaxLength: 4000,
				Paragraph: true,
			},
			{
				ID:        "webserver",
				Title:     "Webserver",
				Question:  "What is your favorite webserver? (e.g. Apache, Nginx etc.)",
				MinLength: 10,
				MaxLength: 4000,
				Paragraph: true,
			},
			{
				ID:        "agreement",
				Title:     "Agreement",
				Question:  "Do you understand that being staff here is a privilege and that you may demoted without warning.",
				MinLength: 5,
				MaxLength: 30,
				Paragraph: true,
			},
		},
	},
}

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

var staffAppComponents [][]discordgo.MessageComponent = make([][]discordgo.MessageComponent, len(staffAppQuestions))

func init() {
	for i, page := range staffAppQuestions {
		for _, v := range page.Questions {
			var style discordgo.TextInputStyle
			if v.Paragraph {
				style = discordgo.TextInputStyleParagraph
			} else {
				style = discordgo.TextInputStyleShort
			}
			staffAppComponents[i] = append(staffAppComponents[i], discordgo.ActionsRow{
				Components: []discordgo.MessageComponent{
					discordgo.TextInput{
						CustomID:    v.ID,
						Style:       style,
						Label:       v.Title,
						Placeholder: v.Question,
						Required:    true,
						MinLength:   v.MinLength,
						MaxLength:   v.MaxLength,
					},
				},
			})
		}
	}
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

func SendRolesMessage(s *discordgo.Session, delAndSend bool) {
	msgs, err := s.ChannelMessages(common.RolesChannel, 100, "", "", "")

	if err != nil {
		panic(err)
	}
	if delAndSend {
		for _, msg := range msgs {
			if msg.Author.ID == s.State.User.ID {
				s.ChannelMessageDelete(common.RolesChannel, msg.ID)
			}
		}
	}

	if delAndSend {
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

		s.ChannelMessageSendComplex(common.RolesChannel, &discordgo.MessageSend{
			Content: "Click the button below to request a data deletion request!\n**This action is irreversible, you will loose all perks you have and all your bots will be deleted permanently**.\nYour vote epoch (when you last voted) will stay as it is temporary (expires after 8 hours) and is needed for anti-vote abuse (to prevent vote spam and vote scams etc.)\n\n*This process is manual and can take up to 24 hours to complete.*",
			Components: []discordgo.MessageComponent{
				discordgo.ActionsRow{
					Components: []discordgo.MessageComponent{
						discordgo.Button{
							CustomID: "ddr",
							Label:    "Data Deletion Request",
						},
					},
				},
			},
		})

		s.ChannelMessageSendComplex(common.RolesChannel, &discordgo.MessageSend{
			Content: "Click the button below to start a staff application",
			Components: []discordgo.MessageComponent{
				discordgo.ActionsRow{
					Components: []discordgo.MessageComponent{
						discordgo.Button{
							CustomID: "baypaw-modal::0",
							Label:    "Apply",
						},
					},
				},
			},
		})
	} else {
		if len(msgs) > 0 {
			rolesMsg = msgs[len(msgs)-1]
		}
	}
	slashbot.AddModalHandler("baypaw-modal", func(context types.SlashContext) string {
		log.Info(context.ModalContext)
		pageInt, err := strconv.Atoi(context.ModalContext)

		if pageInt == 0 {
			baypawApps[context.User.ID] = map[string]interface{}{}
		} else {
			_, ok := baypawApps[context.User.ID]
			if !ok {
				return ""
			}
		}

		log.Info(baypawApps[context.User.ID])

		var questionCollector func(c []discordgo.MessageComponent)

		questionCollector = func(c []discordgo.MessageComponent) {
			for _, v := range c {
				switch vSwitch := v.(type) {
				case *discordgo.ActionsRow:
					questionCollector(vSwitch.Components)
				case *discordgo.TextInput:
					baypawApps[context.User.ID][vSwitch.CustomID] = vSwitch.Value
				}
			}
		}

		questionCollector(context.ModalData.Components)

		if pageInt+1 == len(staffAppQuestions) {
			qibliData := map[string]interface{}{
				"app":          baypawApps[context.User.ID],
				"questions":    staffAppQuestions,
				"app_version":  "2",
				"user":         context.User,
				"qibli_format": "2",
			}

			qibliDataJsonB, err := json.Marshal(qibliData)
			if err != nil {
				log.Error(err)
				slashbot.SendIResponseEphemeral(common.DiscordMain, context.Interaction, err.Error(), false)
			}

			qibliDataJson := string(qibliDataJsonB)

			qibliStorId := common.CreateUUID()

			context.Redis.Set(context.Context, "sapp:"+qibliStorId, qibliDataJson, time.Hour*24*7)

			common.DiscordMain.ChannelMessageSendComplex("936265871784018010", &discordgo.MessageSend{
				Embed: &discordgo.MessageEmbed{
					Title: "Staff Application - Qibli",
					URL:   "https://fateslist.xyz/frostpaw/qibli?data=" + qibliStorId,
				},
				File: &discordgo.File{
					Name:        "qibli.json",
					ContentType: "application/json",
					Reader:      strings.NewReader(qibliDataJson),
				},
			})

			slashbot.SendIResponseEphemeral(common.DiscordMain, context.Interaction, "Staff app submitted!", false)
			return ""
		}

		if err != nil {
			log.Error(err)
			slashbot.SendIResponseEphemeral(common.DiscordMain, context.Interaction, err.Error(), false)
			return ""
		}
		slashbot.SendIResponseFull(
			common.DiscordMain,
			context.Interaction,
			"OK, we've saved your responses to this pane *temporarily*.\n\n**"+staffAppQuestions[pageInt+1].Pre+"**\n\nClick "+staffAppQuestions[pageInt+1].Title+" to go to the next section.",
			false,
			1<<6,
			[]string{},
			nil,
			[]discordgo.MessageComponent{
				discordgo.ActionsRow{
					Components: []discordgo.MessageComponent{
						discordgo.Button{
							CustomID: "baypaw-modal::" + strconv.Itoa(pageInt+1),
							Label:    staffAppQuestions[pageInt+1].Title,
						},
					},
				},
			},
		)
		return ""
	})
}

func MessageHandler(
	ctx context.Context,
	discord *discordgo.Session,
	rdb *redis.Client,
	db *pgxpool.Pool,
	i *discordgo.Interaction,
) {
	if i.Member == nil {
		return
	}
	data := i.MessageComponentData()
	if strings.HasPrefix(data.CustomID, "vr-enable") {
		botId := strings.Split(data.CustomID, "::")[1]
		// Check if they have signed up vote reminders
		var voteReminders pgtype.TextArray

		err := db.QueryRow(ctx, "SELECT vote_reminders::text[] FROM users WHERE user_id = $1", i.Member.User.ID).Scan(&voteReminders)
		if err != nil {
			log.Error(err)
			voteReminders = pgtype.TextArray{
				Elements: []pgtype.Text{},
				Status:   pgtype.Null,
			}
		}

		var hasRemindersEnabled bool
		for _, bot := range voteReminders.Elements {
			if bot.String == botId {
				hasRemindersEnabled = true
				break
			}
		}

		if hasRemindersEnabled {
			slashbot.SendIResponseEphemeral(common.DiscordMain, i, "You already have reminders enabled for this bot!", false)
		} else if len(voteReminders.Elements) > 5 {
			slashbot.SendIResponseEphemeral(common.DiscordMain, i, "You can only have 5 reminders enabled at a time!", false)
		} else {
			db.Exec(
				ctx,
				"UPDATE users SET vote_reminders = vote_reminders || $1 WHERE user_id = $2",
				[]string{botId},
				i.Member.User.ID,
			)
			slashbot.SendIResponseEphemeral(common.DiscordMain, i, "Vote reminders enabled for this bot", false)
		}
	}
	if data.CustomID == "vr-menu" {
		bot := data.Values[0]
		db.Exec(
			ctx,
			"UPDATE users SET vote_reminders = array_remove(vote_reminders, $1) WHERE user_id = $2",
			bot,
			i.Member.User.ID,
		)
		slashbot.SendIResponseEphemeral(common.DiscordMain, i, "Vote reminders disabled for this bot", false)
	}

	if strings.HasPrefix(data.CustomID, "baypaw-modal") {
		page := strings.Split(data.CustomID, "::")[1]
		pageInt, err := strconv.Atoi(page)
		if err != nil {
			log.Error(err)
			return
		}
		err = slashbot.SendModal(
			discord,
			i,
			staffAppQuestions[pageInt].Title,
			"baypaw-modal",
			page,
			staffAppComponents[pageInt],
		)
		log.Error(err)
	}
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
		log.Info(rolesMsg)
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
			return
		}

		rdb.Del(ctx, "vote_lock:"+i.Member.User.ID)
		rdb.Set(ctx, "redeem:"+i.Member.User.ID, "1", time.Hour*24)
		slashbot.SendIResponseEphemeral(common.DiscordMain, i, "You have redeemed your daily free upvote successfully", false)
	} else if data.CustomID == "get-old-roles" {
		slashbot.SendIResponseEphemeral(common.DiscordMain, i, "defer", false)
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
	} else if data.CustomID == "ddr" {
		check := rdb.Exists(ctx, "ddr:"+i.Member.User.ID).Val()
		if check != 0 {
			slashbot.SendIResponseEphemeral(common.DiscordMain, i, "You have already requested a data deletion request!", false)
			return
		}

		g, err := common.DiscordMain.State.Guild(i.GuildID)

		if err != nil {
			slashbot.SendIResponseEphemeral(common.DiscordMain, i, err.Error(), false)
		}

		owner, err := common.DiscordMain.State.Member(i.GuildID, g.OwnerID)

		if err != nil {
			slashbot.SendIResponseEphemeral(common.DiscordMain, i, err.Error(), false)
		}

		common.DiscordMain.ChannelMessageSendComplex(common.AppealsChannel, &discordgo.MessageSend{
			Content: fmt.Sprintf("%s\n\n %s has requested a data deletion request. Please wait for a owner to handle your request.\nIf this was accidental, please immediately ping a staff member!", owner.Mention(), i.Member.User.Mention()),
		})

		rdb.Set(ctx, "ddr:"+i.Member.User.ID, "1", time.Hour*24)
		slashbot.SendIResponseEphemeral(common.DiscordMain, i, "You have requested a data deletion request!\n\n**This process is manual and can take up to 24 hours to complete.**\nIf this was accidental, please immediately ping a staff member!", false)
	}
}
