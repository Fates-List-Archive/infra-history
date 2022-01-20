package admin

import (
	"flamepaw/types"

	"github.com/Fates-List/discordgo"
)

type AdminOp struct {
	InternalName  string                                `json:"internal_name"` // Internal name for enums
	Cooldown      types.CooldownBucket                  `json:"cooldown"`
	Description   string                                `json:"description"`
	MinimumPerm   float32                               `json:"min_perm"`
	BotNeeded     bool                                  `json:"bot_needed"`
	ReasonNeeded  bool                                  `json:"reason_needed"`
	Event         types.APIEvent                        `json:"event"`
	Autocompleter types.Autocompleter                   `json:"-"` // Autocompleter
	Handler       types.SlashHandler                    `json:"-"`
	Server        string                                `json:"server"`        // Slash command server
	SlashOptions  []*discordgo.ApplicationCommandOption `json:"slash_options"` // Slash command options
	SlashRaw      bool                                  `json:"slash_raw"`     // Whether or not to add the bot option
	Critical      bool                                  `json:"critical"`      // Whether or not a command is critical and should be usable without a verification code set
}
