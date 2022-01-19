package types

import (
	"context"
	"strconv"

	"github.com/DisgoOrg/disgo/core"
	"github.com/DisgoOrg/disgo/core/events"
	"github.com/DisgoOrg/disgo/discord"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgx/v4/pgxpool"
)

type StaffRole struct {
	ID           string  `json:"id"`
	StaffID      string  `json:"staff_id"`
	Perm         float32 `json:"perm"`
	FriendlyName string  `json:"fname"`
}

type UserBotAuditLog int

const (
	UserBotApprove UserBotAuditLog = 0
	UserBotDeny    UserBotAuditLog = 1
	UserBotCertify UserBotAuditLog = 2
	UserBotBan     UserBotAuditLog = 3
	UserBotClaim   UserBotAuditLog = 4
	UserBotUnclaim UserBotAuditLog = 5
)

type StaffRoles map[string]StaffRole

type IPCContext struct {
	Me       *core.Bot
	Postgres *pgxpool.Pool
	Redis    *redis.Client
}

type IPCCommand struct {
	Handler func(cmd []string, context IPCContext) string
	MinArgs int
	MaxArgs int
}

type FatesUser struct {
	ID            string `json:"id"`
	Username      string `json:"username"`
	Discriminator string `json:"disc"`
	Avatar        string `json:"avatar"`
	Locale        string `json:"locale"`
	Bot           bool   `json:"bot"`
	Status        Status `json:"status"`
}

type FatesTask struct {
	Op      FatesTaskOp `json:"op"`   // The operation number
	Data    string      `json:"data"` // JSON data in string format
	Context interface{} `json:"ctx"`  // Event Context
}

type WebhookData struct {
	Id        string   `json:"id"`          // Bot/guild id
	Bot       bool     `json:"bot"`         // If this is false, then guild
	Event     APIEvent `json:"event"`       // Event name
	Timestamp float64  `json:"ts"`          // Timestamp
	VoteCount int      `json:"vote_count"`  // Vote Count
	User      string   `json:"user"`        // User
	EventType int      `json:"t,omitempty"` // Event Type
}

type DiscordMessage struct {
	Content      string         `json:"content"`
	Embed        *discord.Embed `json:"embed,omitempty"`
	FileContent  string         `json:"file_content"`
	FileName     string         `json:"file_name"`
	ChannelId    string         `json:"channel_id"`
	MentionRoles []string       `json:"mention_roles,omitempty"`
}

type FatesVote struct {
	User      string        `json:"id"`
	VoteCount int           `json:"votes"`
	Context   interface{}   `json:"ctx"`
	Metadata  EventMetadata `json:"m"`
}

type Event struct {
	Context  interface{}   `json:"ctx"`
	Metadata EventMetadata `json:"m"`
}

type SimpleContext struct {
	User   string  `json:"user"`
	Reason *string `json:"reason"`
}

type EventMetadata struct {
	Event     APIEvent `json:"event"` // Event name
	User      string   `json:"user"`  // User
	Timestamp float64  `json:"ts"`    // Timestamp
	EventId   string   `json:"eid"`   // The event id
	EventType int      `json:"t"`     // Event Type
}

type WebsocketIdentifyPayload struct {
	ID       string `json:"id"`        // ID
	Token    string `json:"token"`     // Token
	Bot      bool   `json:"bot"`       // Bot is true, guild is false
	SendAll  bool   `json:"send_all"`  // Whether to send all prior messages, may dramatically increase startup time
	SendNone bool   `json:"send_none"` // Send none status
}

type WebsocketPayload struct {
	Code              string  `json:"code"`
	Detail            string  `json:"detail"`
	Timestamp         float64 `json:"ts"`
	RequestsRemaining int     `json:"requests_remaining"`
	Control           bool    `json:"control"`
}

// Admin
type StaffPerms struct {
	IsStaff bool `json:"staff"`
	Perm    int  `json:"perm"`
}

type AdminRedisContext struct {
	Reason string `json:"reason"`
}

type CmdContext struct {
	Context     context.Context
	Me          *core.Bot
	Interaction *events.InteractionEvent
	Postgres    *pgxpool.Pool
	Redis       *redis.Client
	User        *core.User
	StaffPerm   float32
	ServerPerm  float32
	Bot         *core.User
	BotState    BotState
	ExtraInfo   map[string]string // This contains reason and owner etc etc
}

type HandlerData struct {
	Context     context.Context
	Me          *core.Bot
	Postgres    *pgxpool.Pool
	Redis       *redis.Client
	Interaction *events.InteractionEvent
	Index       string
}

type SlashCreator func() map[string]SlashCommand
type SlashHandler func(handler HandlerData) string
type Autocompleter func(handler HandlerData) []discord.ApplicationCommandOptionChoiceString

// Intermediate slash command representation
type SlashCommand struct {
	Index         string
	Name          string
	Description   string
	Server        string
	Cooldown      CooldownBucket
	Handler       SlashHandler
	Options       []discord.ApplicationCommandOption
	Autocompleter Autocompleter
	Disabled      bool
}

type AdminOp struct {
	InternalName  string                             `json:"internal_name"` // Internal name for enums
	Cooldown      CooldownBucket                     `json:"cooldown"`
	Description   string                             `json:"description"`
	MinimumPerm   int                                `json:"min_perm"`
	ReasonNeeded  bool                               `json:"reason_needed"`
	Event         APIEvent                           `json:"event"`
	Autocompleter Autocompleter                      `json:"-"` // Autocompleter
	Handler       SlashHandler                       `json:"-"`
	Server        string                             `json:"server"`        // Slash command server
	SlashOptions  []discord.ApplicationCommandOption `json:"slash_options"` // Slash command options
	SlashRaw      bool                               `json:"slash_raw"`     // Whether or not to add the bot option
	Critical      bool                               `json:"critical"`      // Whether or not a command is critical and should be usable without a verification code set
}

type ServerListCommand struct {
	InternalName string                             `json:"internal_name"` // Internal name for enums
	AliasTo      string                             `json:"alias_to"`      // What should this command alias to
	Description  string                             `json:"description"`
	Cooldown     CooldownBucket                     `json:"cooldown"`
	Perm         int                                `json:"perm"`
	Event        APIEvent                           `json:"event"`
	Handler      SlashHandler                       `json:"-"`
	SlashOptions []discord.ApplicationCommandOption `json:"slash_options"` // Slash command options
	Disabled     bool                               `json:"disabled"`
	Server       string                             `json:"server"`
}

type CooldownBucket struct {
	Name         string  `json:"name"`          // Cooldown bucket name
	InternalName string  `json:"internal_name"` // Internal name for use in code
	Time         float32 `json:"time"`          // Time duration
}

var (
	CooldownRequeue  = CooldownBucket{Name: "Requeue Bucket", InternalName: "requeue", Time: 60 * 0.2}
	CooldownBan      = CooldownBucket{Name: "Ban Bucket", InternalName: "ban", Time: 60 * 0.4}
	CooldownTransfer = CooldownBucket{Name: "Transfer Bucket", InternalName: "transfer", Time: 60 * 0.5}
	CooldownReset    = CooldownBucket{Name: "Reset Bucket", InternalName: "reset", Time: 60 * 1.0}
	CooldownLock     = CooldownBucket{Name: "Lock Bucket", InternalName: "lock", Time: 60 * 2.0}
	CooldownDelete   = CooldownBucket{Name: "Delete Bucket", InternalName: "delete", Time: 60 * 3.5}
	CooldownNone     = CooldownBucket{Name: "No cooldown", InternalName: "", Time: 0.0}
)

type StateInterface interface {
	Int() int
	ValStr() string
	Str() string
	Register()
	GetRegistered() []StateInterface
}

var userStateRegister []StateInterface
var botStateRegister []StateInterface
var botFlagRegister []StateInterface

type UserState struct {
	Value       int
	Description string
}

func (s UserState) Int() int {
	return s.Value
}

func (s UserState) ValStr() string {
	return strconv.Itoa(s.Value)
}

func (s UserState) Str() string {
	return s.Description
}

func (s UserState) Register() {
	userStateRegister = append(userStateRegister, s)
}

func (s UserState) GetRegistered() []StateInterface {
	return userStateRegister
}

type BotFlag struct {
	Value       int
	Description string
}

func (s BotFlag) Int() int {
	return s.Value
}

func (s BotFlag) ValStr() string {
	return strconv.Itoa(s.Value)
}

func (s BotFlag) Str() string {
	return s.Description
}

func (s BotFlag) Register() {
	botFlagRegister = append(botFlagRegister, s)
}

func (s BotFlag) GetRegistered() []StateInterface {
	return botFlagRegister
}

// Implements a StateInterface for bots and servers
type BotState struct {
	Value       int
	Description string
}

func (s BotState) Int() int {
	return s.Value
}

func (s BotState) ValStr() string {
	return strconv.Itoa(s.Value)
}

func (s BotState) Str() string {
	return s.Description
}

func (s BotState) Register() {
	botStateRegister = append(botStateRegister, s)
}

func (s BotState) GetRegistered() []StateInterface {
	return botStateRegister
}

func GetStateChoices(s StateInterface) (ch []discord.ApplicationCommandOptionChoice) {
	for _, v := range s.GetRegistered() {
		ch = append(ch, discord.ApplicationCommandOptionChoiceInt{Name: v.Str() + "(" + v.ValStr() + ")", Value: v.Int()})
	}
	return
}

// Bot States
var BotStateApproved = BotState{
	Value:       0,
	Description: "Approved",
}

var BotStatePending = BotState{
	Value:       1,
	Description: "Pending Approval",
}

var BotStateDenied = BotState{
	Value:       2,
	Description: "Denied",
}

var BotStateHidden = BotState{
	Value:       3,
	Description: "Hidden",
}

var BotStateBanned = BotState{
	Value:       4,
	Description: "Banned",
}

var BotStateUnderReview = BotState{
	Value:       5,
	Description: "Under Review",
}

var BotStateCertified = BotState{
	Value:       6,
	Description: "Certified",
}

var BotStateArchived = BotState{
	Value:       7,
	Description: "Archived",
}

var BotStatePrivateViewable = BotState{
	Value:       8,
	Description: "Private but viewable with link (server only)",
}

var BotStatePrivateStaffOnly = BotState{
	Value:       9,
	Description: "This server may only be joined by Fates List Staff (server only)",
}

var BotStateUnknown = BotState{
	Value:       -1,
	Description: "Unknown State",
}

// User States
var UserStateNormal = UserState{
	Value:       0,
	Description: "Normal/No Ban",
}

var UserStateGlobalBan = UserState{
	Value:       1,
	Description: "Global Banned",
}

var UserStateProfileEditBan = UserState{
	Value:       2,
	Description: "Profile Edit Ban",
}

var UserStateUnknown = UserState{
	Value:       -1,
	Description: "Unknown State",
}

// Bot Flags
var BotFlagEditLocked = BotFlag{
	Value:       1,
	Description: "Edit Lock",
}

var BotFlagStaffLocked = BotFlag{
	Value:       2,
	Description: "Staff Lock",
}

var BotFlagStatsLocked = BotFlag{
	Value:       3,
	Description: "Stats Locked",
}

var BotFlagVoteLocked = BotFlag{
	Value:       4,
	Description: "Vote Locked",
}

var BotFlagSystem = BotFlag{
	Value:       5,
	Description: "System Bot",
}

var BotFlagUnknown = BotFlag{
	Value:       -1,
	Description: "Unknown",
}

func init() {
	BotStateApproved.Register()
	BotStatePending.Register()
	BotStateDenied.Register()
	BotStateHidden.Register()
	BotStateBanned.Register()
	BotStateUnderReview.Register()
	BotStateCertified.Register()
	BotStateArchived.Register()
	BotStatePrivateViewable.Register()
	BotStatePrivateStaffOnly.Register()

	UserStateNormal.Register()
	UserStateGlobalBan.Register()
	UserStateProfileEditBan.Register()

	BotFlagEditLocked.Register()
	BotFlagStaffLocked.Register()
	BotFlagStatsLocked.Register()
	BotFlagVoteLocked.Register()
	BotFlagSystem.Register()
}

// State getter
func GetBotState(state int) BotState {
	for _, v := range BotStateUnknown.GetRegistered() {
		if v.Int() == state {
			return v.(BotState)
		}
	}
	return BotStateUnknown
}

func GetBotFlag(state int) BotFlag {
	for _, v := range BotFlagUnknown.GetRegistered() {
		if v.Int() == state {
			return v.(BotFlag)
		}
	}
	return BotFlagUnknown
}

type Status int

const (
	SUnknown = iota
	SOnline  = iota
	SOffline = iota
	SIdle    = iota
	SDnd     = iota
)

type FatesTaskOp int

const (
	OPWebhook = iota // 0
	OPBotEdit = iota // 1
)

type APIEvent int

const (
	EventNone            = -1
	EventBotVote         = 0
	EventBotAdd          = 1
	EventBotEdit         = 2
	EventBotDelete       = 3
	EventBotClaim        = 4
	EventBotApprove      = 5
	EventBotDeny         = 6
	EventBotBan          = 7
	EventBotUnban        = 8
	EventBotRequeue      = 9
	EventBotCertify      = 10
	EventBotUncertify    = 11
	EventBotTransfer     = 12
	EventBotHide         = 13
	EventBotArchive      = 14
	EventBotUnverify     = 15
	EventBotView         = 16
	EventBotInvite       = 17
	EventBotUnclaim      = 18
	EventRootStateUpdate = 19
	EventVoteReset       = 20
	EventVoteResetAll    = 21
	EventBotLock         = 22
	EventBotUnlock       = 23
	EventReviewVote      = 30
	EventReviewAdd       = 31
	EventReviewEdit      = 32
	EventReviewDelete    = 33
	EventResourceAdd     = 40
	EventResourceDelete  = 41
	EventCommandAdd      = 50
	EventCommandDelete   = 51
	EventServerView      = 70
	EventServerVote      = 71
	EventServerInvite    = 72
	EventStaffLock       = 80
	EventStaffUnlock     = 81
)

type WebsocketEvent int

const (
	EventWSIdentity         = 90
	EventWSIdentityResponse = 91
	EventWSKill             = 92
	EventWSStatus           = 93
	EventWSEvent            = 94
)

type WebhookType int

const (
	VoteWebhook    = iota
	DiscordWebhook = iota
	FatesWebhook   = iota
)

type WebhookResolve int

const (
	WebhookPostPending = iota // 0
	WebhookPostError   = iota // 1
	WebhookPostSuccess = iota // 2
)

type WebsocketCloseCode struct {
	Code        int
	Description string
}

var (
	InvalidConn   = WebsocketCloseCode{Code: 4000, Description: "Invalid connection, try again"}
	InvalidAuth   = WebsocketCloseCode{Code: 4004, Description: "Invalid authentication, try again"}
	Ratelimited   = WebsocketCloseCode{Code: 4012, Description: "Ratelimited"}
	InternalError = WebsocketCloseCode{Code: 4500, Description: "Internal Server Error, try reconnecting?"}
)

type InternalUserAuth struct {
	AuthToken string `header:"Authorization" binding:"required"`
}

type UserVote struct {
	UserID string `json:"user_id" binding:"required"`
	BotID  string `json:"bot_id" binding:"-"`
	Test   bool   `json:"test" binding:"-"`
}

type JAPIApp struct {
	Cached bool        `json:"cached"`
	Data   JAPIAppData `json:"data"`
}

type JAPIAppData struct {
	Bot JAPIAppBot `json:"bot"`
}

type JAPIAppBot struct {
	ApproximateGuildCount int `json:"approximate_guild_count"`
}
