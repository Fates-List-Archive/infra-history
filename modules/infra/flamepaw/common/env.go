package common

import (
	"flag"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"runtime"

	"github.com/Fates-List/discordgo"
	log "github.com/sirupsen/logrus"
	"github.com/valyala/fastjson"
)

// Put all env variables here
const version = "2"

// Staff Verification Code (sigh, people don't read staff info anymore)
func VerificationCode(userId string, code string) bool {
	res, err := http.Get("https://lynx.fateslist.xyz/_admin_code_check?user_id=" + userId + "&code=" + code)
	if err != nil {
		log.Error(err)
		return false
	}
	if res.StatusCode == 204 {
		return true
	}
	return false
}

var (
	secretsJsonFile string
	discordJsonFile string
)

var (
	MainBotToken            string
	ServerBotToken          string
	SquirrelflightToken     string
	fetchBot1Token          string // Used for fetching
	ClientSecret            string
	GHWebhookSecret         string
	VoteTokenAccessKey      string
	VoteTokenAccessKeyBytes []byte
	JAPIKey                 string
	MainServer              string
	TestServer              string
	StaffServer             string
	SiteLogs                string
	AppealsChannel          string
	MainSupportChannel      string
	GithubChannel           string
	VoteReminderChannel     string
	CertifiedBotRole        string
	CertifiedDevRole        string
	BotDevRole              string
	RolesChannel            string
	StatsChannel            string
	AccessGrantedRole       string
	TestServerStaffRole     string
	TestServerBotsRole      string
	StaffPingAddRole        string
	ILovePingsRole          string
	NewsPingRole            string
	GiveawayPingRole        string
	BronzeUserRole          string
	CliCmd                  string
	RootPath                string
	PythonPath              string
	Debug                   bool
	RegisterCommands        bool
	IPCOnly                 bool
)

func init() {
	flag.StringVar(&RootPath, "root", "/home/meow/FatesList", "Fates List source directory")
	flag.StringVar(&CliCmd, "cmd", "", "The command to run:\n\tserver: runs the ipc and ws server\n\ttest: runs the unit test system\n\tsite.XXX: run a site command (run=run site, compilestatic=compile static files).\n\tSet PYLOG_LEVEL to set loguru log level to debug")
	flag.StringVar(&PythonPath, "python-path", "/home/meow/venv-next-2022/bin/python", "Path to python interpreter")
	flag.BoolVar(&Debug, "debug", false, "Debug mode")
	flag.BoolVar(&RegisterCommands, "register-only", false, "Only register commands and exit! Overrides --cmd")
	flag.BoolVar(&IPCOnly, "ipc-only", false, "Whether or not this dragon server instance should be a ipc only instance")
	flag.Parse()

	secretsJsonFile = RootPath + "/config/data/secrets.json"
	discordJsonFile = RootPath + "/config/data/discord.json"
	staffRoleFilePath = RootPath + "/config/data/staff_roles.json"

	if CliCmd == "" && !RegisterCommands && !IPCOnly {
		fmt.Println("Version:", version, "\nBuilt with:", runtime.Version())
		flag.Usage()
		os.Exit(3)
	} else if RegisterCommands || IPCOnly {
		CliCmd = "server"
	}

	err := os.Chdir(RootPath)

	if err != nil {
		panic(err)
	}

	var secretsJson, ferr = ioutil.ReadFile(secretsJsonFile)
	var discordJson, ferr2 = ioutil.ReadFile(discordJsonFile)
	if ferr != nil {
		panic(ferr.Error())
	} else if ferr2 != nil {
		panic(ferr2.Error())
	}

	MainBotToken = fastjson.GetString(secretsJson, "token_main")
	ClientSecret = fastjson.GetString(secretsJson, "client_secret")
	ServerBotToken = fastjson.GetString(secretsJson, "token_server")
	SquirrelflightToken = fastjson.GetString(secretsJson, "token_squirrelflight")
	fetchBot1Token = fastjson.GetString(secretsJson, "token_fetch_bot_1")
	JAPIKey = fastjson.GetString(secretsJson, "japi_key")
	GHWebhookSecret = fastjson.GetString(secretsJson, "gh_webhook_secret")
	VoteTokenAccessKey = fastjson.GetString(secretsJson, "vote_token_access_key")
	VoteTokenAccessKeyBytes = []byte(VoteTokenAccessKey)

	var p fastjson.Parser

	v, err := p.Parse(string(discordJson))

	if err != nil {
		panic(err)
	}

	var servers = v.GetObject("servers")

	MainServer = string(servers.Get("main").GetStringBytes())
	TestServer = string(servers.Get("testing").GetStringBytes())
	StaffServer = string(servers.Get("staff").GetStringBytes())

	var channels = v.GetObject("channels")

	SiteLogs = string(channels.Get("bot_logs").GetStringBytes())
	MainSupportChannel = string(channels.Get("main_support_channel").GetStringBytes())
	GithubChannel = string(channels.Get("github_channel").GetStringBytes())
	RolesChannel = string(channels.Get("roles_channel").GetStringBytes())
	AppealsChannel = string(channels.Get("appeals_channel").GetStringBytes())
	VoteReminderChannel = string(channels.Get("vote_reminder_channel").GetStringBytes())
	StatsChannel = string(channels.Get("stats_channel").GetStringBytes())

	var roles = v.GetObject("roles")

	CertifiedBotRole = string(roles.Get("certified_bots_role").GetStringBytes())
	CertifiedDevRole = string(roles.Get("certified_dev_role").GetStringBytes())
	BotDevRole = string(roles.Get("bot_dev_role").GetStringBytes())
	AccessGrantedRole = string(roles.Get("staff_server_access_granted_role").GetStringBytes())
	StaffPingAddRole = string(roles.Get("staff_ping_add_role").GetStringBytes())
	ILovePingsRole = string(roles.Get("i_love_pings_role").GetStringBytes())
	NewsPingRole = string(roles.Get("news_ping_role").GetStringBytes())
	GiveawayPingRole = string(roles.Get("giveaway_ping_role").GetStringBytes())
	BronzeUserRole = string(roles.Get("bronze_user_role").GetStringBytes())
	TestServerBotsRole = string(roles.Get("test_server_bots_role").GetStringBytes())

	permInit()

	log.Info("Environment setup successfully!")
}

func init() {
	var err error
	fetchBot1, err = discordgo.New("Bot " + fetchBot1Token)
	if err != nil {
		panic(err)
	}
}
