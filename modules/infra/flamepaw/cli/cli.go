package cli

import (
	"context"
	"flamepaw/admin"
	"flamepaw/common"
	"flamepaw/ipc"
	"flamepaw/serverlist"
	"flamepaw/slashbot"
	"flamepaw/types"
	"flamepaw/webserver"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/Fates-List/discordgo"
	"github.com/davecgh/go-spew/spew"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

var (
	db               *pgxpool.Pool
	discord          *discordgo.Session
	discordServerBot *discordgo.Session
	rdb              *redis.Client
	ctx              context.Context = context.Background()
	uptimeFirstRun   bool
	errBots          []string = []string{} // List of bots that actually don't exist on main server
	errBotOffline    []string = []string{} // List of bots that are offline
	uptimeRunning    bool
)

func Server() {
	db, err := pgxpool.Connect(ctx, "")
	if err != nil {
		panic(err)
	}

	discord, err = discordgo.New("Bot " + common.MainBotToken)
	if err != nil {
		panic(err)
	}

	common.DiscordMain = discord

	discord.Identify.Intents = discordgo.IntentsGuilds | discordgo.IntentsGuildPresences | discordgo.IntentsGuildMembers | discordgo.IntentsDirectMessages | discordgo.IntentsGuildMessages
	discordServerBot, err = discordgo.New("Bot " + common.ServerBotToken)
	if err != nil {
		panic(err)
	}

	common.DiscordServerList = discordServerBot

	// For now, if we don't get the guild members intent in the future, this will be replaced with approx guild count
	discordServerBot.Identify.Intents = discordgo.IntentsGuilds | discordgo.IntentsGuildMessages

	// Be prepared to remove this handler if we don't get priv intents
	memberHandler := func(s *discordgo.Session, m *discordgo.Member) {
		if common.IPCOnly {
			return
		}
		g, err := discordServerBot.State.Guild(m.GuildID)
		if err != nil {
			log.Error(err)
		}
		err2 := serverlist.AddRecacheGuild(ctx, db, g)
		if err2 != "" {
			log.Error(err2)
		}
	}

	discordServerBot.AddHandler(func(s *discordgo.Session, m *discordgo.GuildMemberAdd) { memberHandler(s, m.Member) })
	discordServerBot.AddHandler(func(s *discordgo.Session, m *discordgo.GuildMemberRemove) { memberHandler(s, m.Member) })
	// End of potentially dangerous (priv code)

	// https://gist.github.com/ryanfitz/4191392
	doEvery := func(d time.Duration, f func(time.Time)) {
		f(time.Now())
		for x := range time.Tick(d) {
			f(x)
		}
	}

	uptimeFunc := func(t time.Time) {
		uptimeRunning = true
		log.Info("Called uptime function at time: ", t)
		bots, err := db.Query(ctx, "SELECT bot_id::text FROM bots WHERE state = $1 OR state = $2", types.BotStateApproved.Int(), types.BotStateCertified.Int())
		if err != nil {
			log.Error(err)
			return
		}
		defer bots.Close()
		i := 0
		errBots = []string{}
		errBotOffline = []string{}
		for bots.Next() {
			var botId pgtype.Text
			bots.Scan(&botId)
			if botId.Status != pgtype.Present {
				log.Error("Bot ID is not present during uptime checks...: ", i)
				continue
			}
			status, err := discord.State.Presence(common.MainServer, botId.String)
			if err != nil {
				_, err := discord.State.Member(common.MainServer, botId.String)
				if err != nil {
					// Bot doesn't actually exist!
					errBots = append(errBots, botId.String)
					continue
				}
			}
			if status == nil || status.Status == discordgo.StatusOffline {
				log.Warning(botId.String, " is offline right now!")
				_, err := db.Exec(ctx, "UPDATE bots SET uptime_checks_failed = uptime_checks_failed + 1, uptime_checks_total = uptime_checks_total + 1 WHERE bot_id = $1", botId.String)
				if err != nil {
					log.Error(err)
				}
				errBotOffline = append(errBotOffline, botId.String)
				continue
			}
			_, err = db.Exec(ctx, "UPDATE bots SET uptime_checks_total = uptime_checks_total + 1 WHERE bot_id = $1", botId.String)
			if err != nil {
				log.Error(err)
			}
			i += 1
		}
		log.Info("Finished uptime checks at time: ", time.Now(), ".\nBots Not Found: ", len(errBots))
		uptimeRunning = false
	}

	onReady := func(s *discordgo.Session, m *discordgo.Ready) {
		log.Info("Logged in as ", m.User.Username)
		if !uptimeFirstRun {
			uptimeFirstRun = true
			go doEvery(5*time.Minute, uptimeFunc)
		}
	}

	discord.AddHandler(func(s *discordgo.Session, m *discordgo.GuildMemberAdd) {
		if common.IPCOnly {
			return
		}

		log.Info("New user found. Handling them...")

		if m.Member.GuildID == common.TestServer {
			if !m.Member.User.Bot {
				_, isStaff, _ := common.GetPerms(s, m.Member.User.ID, 5)
				if isStaff {
					err := s.GuildMemberRoleAdd(m.Member.GuildID, m.Member.User.ID, common.TestServerStaffRole)
					if err != nil {
						log.Error(err)
					}
				}
			}
		}

		if m.Member.GuildID == common.MainServer && m.Member.User.Bot {
			// Auto kick code. Minotaur handles autoroles and does it better than me
			_, err := s.State.Member(common.TestServer, m.Member.User.ID)
			if err != nil {
				return
			}
			s.GuildMemberDeleteWithReason(common.TestServer, m.Member.User.ID, "Done testing and invited to main server")
		}

		if m.Member.GuildID == common.StaffServer && m.Member.User.Bot {
			ts, err := m.Member.JoinedAt.Parse()
			if err != nil {
				log.Error(err)
				ts = time.Now()
			}
			log.Info(time.Now().UnixMicro(), ts.UnixMicro(), time.Now().UnixMicro()-ts.UnixMicro())
			if time.Now().UnixMicro()-ts.UnixMicro() >= 3000000 {
				return
			}
			admin.SilverpeltStaffServerProtect(s, m.Member.User.ID)
		}
	})

	discord.AddHandler(onReady)
	discordServerBot.AddHandler(onReady)

	// Slash command handling
	iHandle := func(s *discordgo.Session, i *discordgo.Interaction, bot int) {
		if i.Type == discordgo.InteractionApplicationCommand {
			log.WithFields(log.Fields{
				"i":   spew.Sdump(i),
				"bot": bot,
			}).Info("Going to handle interaction")
		}
		go slashbot.SlashHandler(
			ctx,
			s,
			rdb,
			db,
			i,
		)
	}

	prefixSupport := func(s *discordgo.Session, m *discordgo.MessageCreate, n int) {
		// We handle a messageCreate as a interaction
		if m.Message.Member == nil {
			return
		}
		m.Member.User = m.Author
		for _, roleID := range m.Member.Roles {
			role, err := s.State.Role(m.Message.GuildID, roleID)
			if err != nil {
				continue
			}
			m.Member.Permissions |= role.Permissions
		}

		// Parse the interaction
		var name string
		var options []*discordgo.ApplicationCommandInteractionDataOption
		if strings.HasPrefix(m.Message.Content, "%") {
			cmdList := strings.Split(m.Message.Content, " ")
			name = cmdList[0][1:]
			for i, v := range cmdList {
				// Ignore first
				if i == 0 {
					continue
				}
				argDat := strings.SplitN(v, ":", 2)
				if len(argDat) != 2 {
					continue
				}

				options = append(options, &discordgo.ApplicationCommandInteractionDataOption{
					Name:  argDat[0],
					Type:  discordgo.ApplicationCommandOptionString,
					Value: argDat[1],
				})
			}
		} else {
			// Not for us
			return
		}

		spoofInteraction := &discordgo.Interaction{
			Type: discordgo.InteractionApplicationCommand,
			Data: discordgo.ApplicationCommandInteractionData{
				ID:       m.Message.ID,
				Name:     name,
				Resolved: &discordgo.ApplicationCommandInteractionDataResolved{}, // empty for now
				TargetID: m.Message.ID,
				Options:  options,
			},
			ID:        m.Message.ID,
			Message:   m.Message,
			GuildID:   m.Message.GuildID,
			ChannelID: m.Message.ChannelID,
			Member:    m.Message.Member,
			User:      m.Message.Member.User,
			Token:     "prefixCmd",
		}
		iHandle(s, spoofInteraction, 0)
	}

	discord.AddHandler(func(s *discordgo.Session, m *discordgo.MessageCreate) {
		prefixSupport(s, m, 0)
	})
	discordServerBot.AddHandler(func(s *discordgo.Session, m *discordgo.MessageCreate) {
		prefixSupport(s, m, 1)
	})

	discord.AddHandler(func(s *discordgo.Session, i *discordgo.InteractionCreate) { iHandle(s, i.Interaction, 0) })
	discordServerBot.AddHandler(func(s *discordgo.Session, i *discordgo.InteractionCreate) { iHandle(s, i.Interaction, 1) })
	discordServerBot.AddHandler(func(s *discordgo.Session, gc *discordgo.GuildCreate) {
		if common.IPCOnly {
			return
		}
		log.Info("Adding guild " + gc.Guild.ID + " (" + gc.Guild.Name + ")")
		err := serverlist.AddRecacheGuild(ctx, db, gc.Guild)
		if err != "" {
			log.Error(err)
		}
		rdb.Del(ctx, "pendingdel-"+gc.Guild.ID)
		db.Exec(ctx, "UPDATE servers SET state = $1, deleted = false WHERE guild_id = $2 AND deleted = true AND state = $3", types.BotStateApproved.Int(), gc.Guild.ID, types.BotStatePrivateViewable.Int())
	})
	discordServerBot.AddHandler(func(s *discordgo.Session, gc *discordgo.GuildDelete) {
		if common.IPCOnly {
			return
		}
		log.Info("Left guild " + gc.Guild.ID + "(" + gc.Guild.Name + ")")
		rdb.Set(ctx, "pendingdel-"+gc.Guild.ID, 0, 0)

		time.AfterFunc(1*time.Minute, func() {
			if rdb.Exists(ctx, "pendingdel-"+gc.Guild.ID).Val() != 0 {
				db.Exec(ctx, "UPDATE servers SET state = $1, deleted = true WHERE guild_id = $1", types.BotStatePrivateViewable.Int(), gc.Guild.ID)
			}
		})
	})

	err = discord.Open()
	if err != nil {
		panic(err)
	}
	err = discordServerBot.Open()
	if err != nil {
		panic(err)
	}

	go slashbot.SetupSlash(discord, admin.CmdInit)
	go slashbot.SetupSlash(discordServerBot, serverlist.CmdInit)

	rdb = redis.NewClient(&redis.Options{
		Addr:     "localhost:1001",
		Password: "",
		DB:       1,
	})

	// Delete socket file
	if !common.IPCOnly {
		os.Remove("/home/meow/fatesws.sock")
	}

	// Channel for signal handling
	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs,
		syscall.SIGINT,
		syscall.SIGQUIT)

	// Start IPC code
	if !common.RegisterCommands {
		go ipc.StartIPC(db, rdb)
		if !common.IPCOnly {
			go webserver.StartWebserver(db, rdb)
		}
	}
	s := <-sigs
	log.Info("Going to exit gracefully due to signal", s, "\n")
	if !common.RegisterCommands {
		ipc.SignalHandle(s, rdb)
	}

	// Close all connections
	db.Close()
	rdb.Close()
	discord.Close()
	discordServerBot.Close()

	os.Exit(0)
}
