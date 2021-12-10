package server

import (
	"context"
	"dragon/admin"
	"dragon/common"
	"dragon/ipc"
	"dragon/serverlist"
	"dragon/slashbot"
	"dragon/types"
	"dragon/webserver"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/Fates-List/discordgo"
	"github.com/davecgh/go-spew/spew"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

var (
	db               *pgxpool.Pool
	discord          *discordgo.Session
	discordServerBot *discordgo.Session
	rdb              *redis.Client
	ctx              context.Context = context.Background()
)

func DragonServer() {
	db, err := pgxpool.Connect(ctx, "")
	if err != nil {
		panic(err)
	}

	discord, err = discordgo.New("Bot " + common.MainBotToken)
	if err != nil {
		panic(err)
	}

	common.DiscordMain = discord

	discord.Identify.Intents = discordgo.IntentsGuilds | discordgo.IntentsGuildPresences | discordgo.IntentsGuildMembers | discordgo.IntentsDirectMessages | discordgo.IntentsGuildMessages | discordgo.IntentsGuildMembers
	discordServerBot, err = discordgo.New("Bot " + common.ServerBotToken)
	if err != nil {
		panic(err)
	}

	// For now, if we don't get the guild members intent in the future, this will be replaced with approx guild count
	discordServerBot.Identify.Intents = discordgo.IntentsGuilds | discordgo.IntentsGuildMembers

	// Be prepared to remove this handler if we don't get priv intents
	memberHandler := func(s *discordgo.Session, m *discordgo.Member) {
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

	onReady := func(s *discordgo.Session, m *discordgo.Ready) {
		log.Info("Logged in as ", m.User.Username)
	}

	discord.AddHandler(onReady)
	discordServerBot.AddHandler(onReady)

	// Slash command handling
	iHandle := func(s *discordgo.Session, i *discordgo.InteractionCreate, bot int) {
		log.WithFields(log.Fields{
			"i":   spew.Sdump(i.Interaction),
			"bot": bot,
		}).Info("Going to handle interaction")
		slashbot.SlashHandler(
			ctx,
			s,
			rdb,
			db,
			i,
		)
	}

	discord.AddHandler(func(s *discordgo.Session, i *discordgo.InteractionCreate) { iHandle(s, i, 0) })
	discordServerBot.AddHandler(func(s *discordgo.Session, i *discordgo.InteractionCreate) { iHandle(s, i, 1) })
	discordServerBot.AddHandler(func(s *discordgo.Session, gc *discordgo.GuildCreate) {
		log.Info("Adding guild " + gc.Guild.ID + " (" + gc.Guild.Name + ")")
		err := serverlist.AddRecacheGuild(ctx, db, gc.Guild)
		if err != "" {
			log.Error(err)
		}
		rdb.Del(ctx, "pendingdel-"+gc.Guild.ID)
		db.Exec(ctx, "UPDATE servers SET state = $1, deleted = false WHERE guild_id = $2 AND deleted = true AND state = $3", types.BotStateApproved.Int(), gc.Guild.ID, types.BotStatePrivateViewable.Int())
	})
	discordServerBot.AddHandler(func(s *discordgo.Session, gc *discordgo.GuildDelete) {
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
	os.Remove("/home/meow/fatesws.sock")

	// Channel for signal handling
	sigs := make(chan os.Signal, 1)
	signal.Notify(sigs,
		syscall.SIGINT,
		syscall.SIGQUIT)

	// Start IPC code
	if !common.RegisterCommands {
		go ipc.StartIPC(db, discord, discordServerBot, rdb)
		go webserver.StartWebserver(db, rdb)
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
