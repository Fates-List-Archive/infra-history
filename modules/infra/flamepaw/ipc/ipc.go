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

	ipcContext := types.IPCContext{
		Redis:    redisClient,
		Postgres: postgres,
	}

	handleMsg := func(msg redis.Message) {
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
