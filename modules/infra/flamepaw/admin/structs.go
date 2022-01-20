package admin

import (
	"flamepaw/types"

	"github.com/Fates-List/discordgo"
)

type AdminOp struct {
	InternalName   string // Internal name for enums
	Cooldown       types.CooldownBucket
	Description    string
	MinimumPerm    float32
	ReasonNeeded   bool
	Event          types.APIEvent
	Autocompleter  types.Autocompleter // Autocompleter
	Handler        types.SlashHandler
	Server         string                                // Slash command server
	SlashOptions   []*discordgo.ApplicationCommandOption // Slash command options
	SlashRaw       bool                                  // Whether or not to add the bot option
	Critical       bool                                  // Whether or not a command is critical and should be usable without a verification code set
	SupportsGuilds bool                                  // Command supports guilds
}
