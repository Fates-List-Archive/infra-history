package admin

import (
	"flamepaw/common"
	"flamepaw/types"

	"github.com/Fates-List/discordgo"
)

const embedColorGood = 0x00ff00
const embedColorBad = 0xe74c3c
const perMessageQueueCount = 4 // 4 bots per message

var (
	commands         = make(map[string]AdminOp)
	commandNameCache = make(map[string]string)
	staffOnlyFlags   = []types.BotFlag{types.BotFlagStatsLocked, types.BotFlagVoteLocked, types.BotFlagSystem, types.BotFlagStaffLocked}
)

// Admin OP Getter
func CmdInit() map[string]types.SlashCommand {
	// Mock is only here for registration, actual code is on slashbot

	commands["MOCK"] = AdminOp{
		InternalName: "mock",
		Cooldown:     types.CooldownNone,
		Description:  "Mocks a guild in server listing",
		SlashRaw:     true,
		SlashOptions: []*discordgo.ApplicationCommandOption{
			{
				Type:        discordgo.ApplicationCommandOptionString,
				Name:        "guild",
				Description: "Guild to mock",
			},
		},
		Server: common.StaffServer,
	}

	// Load command name cache to map internal name to the command
	for cmdName, v := range commands {
		commandNameCache[v.InternalName] = cmdName
	}
	return slashIr()
}
