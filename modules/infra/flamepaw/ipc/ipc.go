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

	"github.com/davecgh/go-spew/spew"
	"github.com/go-redis/redis/v8"
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
