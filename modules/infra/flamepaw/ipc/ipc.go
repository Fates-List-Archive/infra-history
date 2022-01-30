package ipc

import (
	"context"
	"flamepaw/common"
	"flamepaw/types"
	"flamepaw/webserver"
	"os"
	"strconv"
	"strings"
	"time"

	jsoniter "github.com/json-iterator/go"

	"github.com/Fates-List/discordgo"
	"github.com/davecgh/go-spew/spew"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

var json = jsoniter.ConfigCompatibleWithStandardLibrary

const (
	workerChannel     string        = "_worker_fates"
	commandExpiryTime time.Duration = 30 * time.Second
	ipcVersion        string        = "3"
)

var (
	ctx                  = context.Background()
	connected   bool     = false
	ipcIsUp     bool     = true
	pids        []string // Just use string slice here for storage of pids
	sessionId   string   // Session id
	degraded    int      = 0
	degradedStr string   = strconv.Itoa(degraded)
	guilds      []string
	allowCmd    bool = true
	pubsub      *redis.PubSub
)

var ipcActions = make(map[string]types.IPCCommand)

func ElementInSlice[T comparable](slice []T, elem T) bool {
	for i := range slice {
		if slice[i] == elem {
			return true
		}
	}
	return false
}

func setupCommands() {
	// Define all IPC commands here

	// PING <COMMAND ID>
	ipcActions["PING"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			return "PONG V" + ipcVersion + " " + degradedStr
		},
		MinArgs: -1,
		MaxArgs: -1,
	}

	// RESTART * | RESTART <PID1> <PID2>
	ipcActions["RESTART"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			if cmd[1] != "*" {
				var npids []string = make([]string, 0, cap(pids)+1)
				for _, pid := range pids {
					if pid != cmd[1] {
						npids = append(npids, pid)
					}
				}
				pids = npids
			} else {
				pids = nil
			}
			return ""
		},
		MinArgs: -1,
		MaxArgs: -1,
	}

	// UP <SESSION ID> <PID> <AMT OF WORKERS>
	ipcActions["UP"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			worker_amt, err := strconv.ParseInt(cmd[3], 0, 64)
			if err != nil {
				log.Error(err)
				return err.Error()
			}

			if sessionId == "" {
				sessionId = cmd[1]
			} else if sessionId != cmd[1] {
				// New session
				pids = make([]string, 0, worker_amt)
				sessionId = cmd[1]
			}

			if int64(len(pids)) >= worker_amt {
				pids = make([]string, 0, worker_amt)
				context.Redis.Publish(ctx, workerChannel, "REGET 1")
				log.Warn("Sent REGET due to a invalid state (1)")
				return ""
			} else {
				pids = append(pids, cmd[2])
			}

			if int64(len(pids)) == worker_amt {
				pids_str := strings.Join(pids, " ")
				context.Redis.Publish(ctx, workerChannel, "FUP "+sessionId+" "+pids_str)
			}
			return ""
		},
		MinArgs: 4,
		MaxArgs: 4,
	}

	// WORKERS <COMMAND ID>
	ipcActions["WORKERS"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			workers, err := json.Marshal(pids)
			if err != nil {
				log.Error(err)
				return "[]"
			}
			return string(workers)
		},
	}

	// GETCH <COMMAND ID> <USER ID>
	ipcActions["GETCH"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			var user *discordgo.User
			member, err := common.DiscordMain.State.Member(common.MainServer, cmd[2])
			if err == nil {
				log.Debug("Using user from member cache")
				user = member.User
			} else {
				user, err = common.DiscordMain.User(cmd[2])
				if err != nil {
					log.Warn(err)
					return "-1"
				}
			}

			fatesUser := &types.FatesUser{
				ID:            user.ID,
				Username:      user.Username,
				Discriminator: user.Discriminator,
				Bot:           user.Bot,
				Locale:        user.Locale,
				Avatar:        user.AvatarURL(""),
				Status:        types.SUnknown,
			}
			got := false
			for _, guild := range guilds {
				if got {
					break
				}
				log.Debug("Looking at guild: ", guild)
				p, err := common.DiscordMain.State.Presence(guild, user.ID)
				if err != nil {
					log.Warn(err)
				}
				if err == nil {
					switch p.Status {
					case discordgo.StatusOnline:
						fatesUser.Status = types.SOnline
					case discordgo.StatusIdle:
						fatesUser.Status = types.SIdle
					case discordgo.StatusDoNotDisturb:
						fatesUser.Status = types.SDnd
					case discordgo.StatusInvisible, discordgo.StatusOffline:
						fatesUser.Status = types.SOffline
					}
					got = true
				}
			}

			userJson, err := json.Marshal(fatesUser)
			if err != nil {
				log.Error(err)
				return "-2"
			}
			userJsonStr := string(userJson)
			log.Debug("User JSON: ", userJsonStr)
			return userJsonStr

		},
		MinArgs: 3,
		MaxArgs: 3,
	}

	// ADDWSEVENT <COMMAND ID> <BOT ID> <EVENT ID> <BOT/GUILD 1/0> <MESSAGE ID (EVENT REDIS ID)>
	// Returns 0 on success
	ipcActions["ADDWSEVENT"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			eventRedis := context.Redis.Get(ctx, cmd[5]).Val()
			if eventRedis == "" {
				return "-1"
			}

			var channel string
			if cmd[4] == "1" {
				channel = "bot-" + cmd[2]
			} else {
				channel = "server-" + cmd[2]
			}

			var event map[string]interface{}

			err := json.Unmarshal([]byte(eventRedis), &event)

			if err != nil {
				log.Error(err)
				return err.Error()
			}

			common.AddWsEvent(ctx, context.Redis, channel, cmd[3], event)
			return "0"
		},
		MinArgs: 6,
		MaxArgs: 6,
	}

	// ROLES <COMMAND ID> <USER ID>
	// Returns roles as space seperated string on success
	ipcActions["ROLES"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			// Try to get from cache
			res := context.Redis.Get(ctx, "roles-"+cmd[2]).Val()
			if res == "" {
				member, err := common.DiscordMain.State.Member(common.MainServer, cmd[2])
				if err != nil {
					log.Warn(err)
					res = "-1"
				} else {
					res = strings.Join(member.Roles, " ")
					context.Redis.Set(ctx, "roles-"+cmd[2], res, 120*time.Second)
				}
			}
			return res
		},
		MinArgs: 3,
		MaxArgs: 3,
	}

	// GETPERM <COMMAND ID> <USER ID>
	ipcActions["GETPERM"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			perms, _, _ := common.GetPerms(common.DiscordMain, cmd[2], 0)
			res, err := json.Marshal(perms)
			if err != nil {
				log.Warn(err)
				return "-1"
			}
			return string(res)
		},
		MinArgs: 3,
		MaxArgs: 3,
	}

	// SENDMSG <COMMAND ID> <MESSAGE ID>
	ipcActions["SENDMSG"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			msg_id := cmd[2]
			msg := context.Redis.Get(ctx, msg_id).Val()
			if msg == "" {
				log.Error("No JSON found")
				return "0"
			}

			var message types.DiscordMessage
			err := json.Unmarshal([]byte(msg), &message)
			if err != nil {
				log.Warn(err)
				return "0"
			}

			if message.FileContent != "" && message.FileName == "" {
				message.FileName = "default.txt"
			}

			messageSend := discordgo.MessageSend{
				Content: message.Content,
				Embed:   message.Embed,
				TTS:     false,
				AllowedMentions: &discordgo.MessageAllowedMentions{
					Roles: message.MentionRoles,
				},
				File: &discordgo.File{
					Name:        message.FileName,
					ContentType: "application/octet-stream",
					Reader:      strings.NewReader(message.FileContent),
				},
			}

			_, err = common.DiscordMain.ChannelMessageSendComplex(message.ChannelId, &messageSend)
			if err != nil {
				log.Error(err)
				return "0"
			}
			return "1"
		},
		MinArgs: 3,
		MaxArgs: 3,
	}

	// SUPPORT <COMMAND ID> <USER ID>
	ipcActions["SUPPORT"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			userId := cmd[2]
			mainGuild, err := common.DiscordMain.State.Guild(common.MainServer)
			user, err := common.DiscordMain.State.Member(common.MainServer, userId)

			if err != nil {
				log.Warn(err)
				return "User not found"
			}

			var flag bool = false
			if err == nil {
				// Check if threads are supported
				for _, v := range mainGuild.Features {
					if v == "PRIVATE_THREADS" {
						flag = true
					}
				}
			} else {
				log.Warn(err.Error() + "... Trying to create private thread anyways!")
				flag = true
			}

			if !flag {
				return "Private threads require more boosts! Please consider boosting :heart:"
			}

			var username string
			if len(user.User.Username) > 70 {
				username = user.User.Username[:70]
			} else {
				username = user.User.Username
			}

			threadList, err := common.DiscordMain.ThreadsListActive(common.MainServer)
			if err != nil {
				return err.Error()
			}

			for _, v := range threadList.Threads {
				if v.ParentID != common.MainSupportChannel {
					continue
				} else if strings.HasPrefix(v.Name, "Support for ") && strings.Contains(v.Name, user.User.ID) {
					if v.ThreadMetadata.Archived || v.ThreadMetadata.Locked {
						continue
					}
					return "You already have an active thread"
				}
			}

			thread, err := common.DiscordMain.ThreadStartWithoutMessage(common.MainSupportChannel, &discordgo.ThreadCreateData{
				Name:                "Support for " + username + "-" + user.User.Discriminator + " (" + user.User.ID + ")",
				AutoArchiveDuration: discordgo.ArchiveDuration3Days,
				Type:                discordgo.ChannelTypeGuildPrivateThread,
				Invitable:           false,
			})
			if err != nil {
				return err.Error()
			}

			msg := discordgo.MessageSend{
				Content: "@everyone <@&836349482340843572>\n\n" + user.User.Mention() + " has started a support thread.\n\n**Please kindly wait for staff to arrive!**",
			}

			_, err = common.DiscordMain.ChannelMessageSendComplex(thread.ID, &msg)

			return "0"
		},
		MinArgs: 3,
		MaxArgs: 3,
	}

	// CMDLIST <COMMAND ID>
	ipcActions["CMDLIST"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			return spew.Sdump("IPC Commands loaded: ", ipcActions)
		},
	}

	// DOCS
	ipcActions["DOCS"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			return webserver.Docs
		},
	}

	// GUILDINVITE <COMMAND ID> <GUILD ID> <USER ID>
	ipcActions["GUILDINVITE"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			guildId := cmd[2]
			userId := cmd[3]
			log.Info("Creating invite for user ", userId)
			var state pgtype.Int4
			var inviteUrl pgtype.Text
			var inviteChannel pgtype.Text
			var finalInv string
			var userWhitelist pgtype.TextArray
			var userBlacklist pgtype.TextArray
			var loginRequired pgtype.Bool
			err := context.Postgres.QueryRow(ctx, "SELECT state, invite_url, invite_channel, user_whitelist, user_blacklist, login_required FROM servers WHERE guild_id = $1", guildId).Scan(&state, &inviteUrl, &inviteChannel, &userWhitelist, &userBlacklist, &loginRequired)
			if err != nil {
				log.Error(err)
				return "Something went wrong: " + err.Error()
			}
			if types.GetBotState(int(state.Int)) == types.BotStatePrivateViewable {
				return "This server is private and not accepting invites at this time!"
			} else if types.GetBotState(int(state.Int)) == types.BotStateBanned {
				return "This server has been banned from Fates List. If you are a staff member, contact Fates List Support for more information."
			} else if types.GetBotState(int(state.Int)) == types.BotStatePrivateStaffOnly {
				if userId == "0" {
					if guildId == common.StaffServer {
						return "You need to login as a Fates List Staff Member (for new staff, this is just your discord login) to join this server"
					}
					return "Login to Fates List before trying to join this server"
				}
				// The needed perm
				var perm float32 = 2
				if guildId == common.StaffServer {
					// Staff server exception, only need permlevel of 2 for staff server
					perm = 2
				}
				_, isStaff, _ := common.GetPerms(common.DiscordMain, userId, perm)
				if !isStaff {
					return "This server is only open to Fates List Staff Members at this time."
				}
			} else if loginRequired.Bool && userId == "0" {
				return "This server requires you to be logged in to join it!"
			}

			var whitelisted bool
			if userWhitelist.Status == pgtype.Present && len(userWhitelist.Elements) > 0 {
				if !ElementInSlice(userWhitelist.Elements, pgtype.Text{String: userId, Status: pgtype.Present}) {
					return "You need to be whitelisted to join this server!"
				}
				whitelisted = true
			}

			if !whitelisted && userBlacklist.Status == pgtype.Present && len(userBlacklist.Elements) > 0 {
				if ElementInSlice(userBlacklist.Elements, pgtype.Text{String: userId, Status: pgtype.Present}) {
					return "You have been blacklisted from joining this server!"
				}
			}

			if inviteUrl.Status != pgtype.Present || inviteUrl.String == "" {
				// Create invite using serverlist bot
				guild, err := common.DiscordServerList.State.Guild(guildId)
				if err != nil {
					log.Error(err)
					return "Something went wrong: " + err.Error()
				}

				var channelId string
				if inviteChannel.Status == pgtype.Present {
					channelId = inviteChannel.String
				} else {
					channelId = guild.RulesChannelID
					if channelId == "" {
						channelId = guild.SystemChannelID
					}
					if channelId == "" {
						channelId = guild.Channels[0].ID
					}
					if channelId == "" {
						return "Could not find channel to invite you to... Please ask the owner of this server to set an invite or set the invite channel for this server"
					}
				}

				invite, err := common.DiscordServerList.ChannelInviteCreateWithReason(channelId, "Created invite for user: "+userId, discordgo.Invite{
					MaxAge:    60 * 15,
					MaxUses:   1,
					Temporary: false,
					Unique:    true,
				})
				if err != nil {
					log.Error(err)
					return "Something went wrong: " + err.Error()
				}
				finalInv = "https://discord.gg/" + invite.Code
			} else {
				finalInv = inviteUrl.String
			}
			context.Postgres.Exec(ctx, "UPDATE servers SET invite_amount = invite_amount + 1 WHERE guild_id = $1", guildId)
			return finalInv
		},
		MinArgs: 4,
		MaxArgs: 4,
	}
}

func StartIPC(postgres *pgxpool.Pool, redisClient *redis.Client) {
	setupCommands()
	u_guilds, err := common.DiscordMain.UserGuilds(100, "", "")
	if err != nil {
		panic(err)
	}

	for _, u_guild := range u_guilds {
		log.Info("Got guild ", u_guild.ID, " for precense check")
		guilds = append(guilds, u_guild.ID)
	}

	pubsub = redisClient.Subscribe(ctx, workerChannel)
	defer pubsub.Close()
	_, err = pubsub.Receive(ctx)
	if err != nil {
		panic(err)
	}

	ch := pubsub.Channel()

	send_err := redisClient.Publish(ctx, workerChannel, "PREPARE IPC").Err()
	if send_err != nil {
		panic(send_err)
	}

	ipcContext := types.IPCContext{
		Redis:    redisClient,
		Postgres: postgres,
	}

	handleMsg := func(msg redis.Message) {
		if !connected {
			connected = true
			log.Debug("Announcing that we are up")
			err = redisClient.Publish(ctx, workerChannel, "REGET 2").Err()
			if err != nil {
				log.Warn(err)
				connected = false
			}
		}
		op := strings.Split(msg.Payload, " ")
		if len(op) < 2 {
			return
		}

		log.WithFields(log.Fields{
			"name": op[0],
			"args": op[1:],
			"pids": pids,
		}).Info("Got IPC Command ", op[0])

		cmd_id := op[1]

		if val, ok := ipcActions[op[0]]; ok {
			// Check minimum args
			if len(op) < val.MinArgs && val.MinArgs > 0 {
				return
			}

			// Similarly, check maximum
			if len(op) > val.MaxArgs && val.MaxArgs > 0 {
				return
			}

			res := val.Handler(op, ipcContext)
			redisClient.Set(ctx, cmd_id, res, commandExpiryTime)
		}
	}

	for msg := range ch {
		if allowCmd {
			go handleMsg(*msg)
		}
	}
}

func SignalHandle(s os.Signal, rdb *redis.Client) {
	allowCmd = false
	if ipcIsUp {
		ipcIsUp = false
		send_err := rdb.Publish(ctx, workerChannel, "RESTART *").Err()
		if send_err != nil {
			log.Error(send_err)
		}
		pubsub.Close()
		time.Sleep(1 * time.Second)
	}
}
