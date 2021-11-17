package ipc

import (
	"context"
	"dragon/admin"
	"dragon/common"
	"dragon/types"
	"encoding/json"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/Fates-List/discordgo"
	"github.com/davecgh/go-spew/spew"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

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
				context.Redis.Publish(ctx, workerChannel, "REGET "+sessionId+" 1")
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

	// GETCH <COMMAND ID> <USER ID>
	ipcActions["GETCH"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			var user *discordgo.User
			member, err := context.Discord.State.Member(common.MainServer, cmd[2])
			if err == nil {
				log.Debug("Using user from member cache")
				user = member.User
			} else {
				user, err = context.Discord.User(cmd[2])
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
				p, err := context.Discord.State.Presence(guild, user.ID)
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

	// ROLES <COMMAND ID> <USER ID>
	ipcActions["ROLES"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			// Try to get from cache
			res := context.Redis.Get(ctx, "roles-"+cmd[2]).Val()
			if res == "" {
				member, err := context.Discord.State.Member(common.MainServer, cmd[2])
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
			perms := common.StaffRoles["user"]
			member, err := context.Discord.State.Member(common.MainServer, cmd[2])
			if err != nil {
				log.Warn(err)
			} else {
				perms = common.GetUserPerms(member.Roles)
			}
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

			_, err = context.Discord.ChannelMessageSendComplex(message.ChannelId, &messageSend)
			if err != nil {
				log.Error(err)
				return "0"
			}
			return "1"
		},
		MinArgs: 3,
		MaxArgs: 3,
	}

	// BTADD <COMMAND ID> <TASK ID>
	ipcActions["BTADD"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			task_id := cmd[2]
			context.Redis.RPush(ctx, "bt_ongoing", task_id)
			go taskHandle(ctx, context.Discord, context.Redis, context.Postgres, task_id)
			return "0"
		},
		MinArgs: 3,
		MaxArgs: 3,
	}

	// GETADMINOPS <COMMAND ID>
	ipcActions["GETADMINOPS"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			ok, commands := admin.CommandsToJSON()
			if !ok {
				return ""
			} else {
				return string(commands)
			}
		},
	}

	// ADMINCMDLIST <COMMAND ID>
	ipcActions["ADMINCMDLIST"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			return admin.GetCommandSpew()
		},
	}

	// CMDLIST <COMMAND ID>
	ipcActions["CMDLIST"] = types.IPCCommand{
		Handler: func(cmd []string, context types.IPCContext) string {
			return spew.Sdump("IPC Commands loaded: ", ipcActions)
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
			err := context.Postgres.QueryRow(ctx, "SELECT state, invite_url, invite_channel FROM servers WHERE guild_id = $1", guildId).Scan(&state, &inviteUrl, &inviteChannel)
			if err != nil {
				log.Error(err)
				return "Something went wrong: " + err.Error()
			}
			if types.GetBotState(int(state.Int)) == types.BotStatePrivateViewable {
				return "This server is private and not accepting invites at this time!"
			}
			if inviteUrl.Status != pgtype.Present || inviteUrl.String == "" {
				// Create invite using serverlist bot
				guild, err := context.ServerList.State.Guild(guildId)
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

				invite, err := context.ServerList.ChannelInviteCreateWithReason(channelId, "Created invite for user: "+userId, discordgo.Invite{
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

func StartIPC(dbpool *pgxpool.Pool, discord *discordgo.Session, serverlist *discordgo.Session, rdb *redis.Client) {
	setupCommands()
	u_guilds, err := discord.UserGuilds(100, "", "")
	if err != nil {
		panic(err)
	}

	for _, u_guild := range u_guilds {
		log.Info("Got guild ", u_guild.ID, " for precense check")
		guilds = append(guilds, u_guild.ID)
	}

	pubsub = rdb.Subscribe(ctx, workerChannel)
	defer pubsub.Close()
	_, err = pubsub.Receive(ctx)
	if err != nil {
		panic(err)
	}

	ch := pubsub.Channel()

	send_err := rdb.Publish(ctx, workerChannel, "PREPARE IPC").Err()
	if send_err != nil {
		panic(send_err)
	}

	ipcContext := types.IPCContext{
		Discord:    discord,
		Redis:      rdb,
		Postgres:   dbpool,
		ServerList: serverlist,
	}

	handleMsg := func(msg redis.Message) {
		if !connected {
			connected = true
			log.Debug("Announcing that we are up")
			err = rdb.Publish(ctx, workerChannel, "REGET 2").Err()
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
			"command_name": op[0],
			"args":         op[1:],
			"pids":         pids,
		}).Info("Got command ", op[0])

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
			rdb.Set(ctx, cmd_id, res, commandExpiryTime)
		}
	}

	// Get all tasks first
	done := false
	for !done {
		cmd_id := rdb.RPop(ctx, "bt_ongoing").Val()
		if cmd_id == "" {
			done = true
		} else {
			go taskHandle(ctx, discord, rdb, dbpool, cmd_id)
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
