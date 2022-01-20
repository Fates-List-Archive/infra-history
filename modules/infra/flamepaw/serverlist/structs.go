package serverlist

import (
	"flamepaw/types"

	"github.com/Fates-List/discordgo"
)

type ServerListCommand struct {
	InternalName string                                `json:"internal_name"` // Internal name for enums
	AliasTo      string                                `json:"alias_to"`      // What should this command alias to
	Description  string                                `json:"description"`
	Cooldown     types.CooldownBucket                  `json:"cooldown"`
	Perm         int                                   `json:"perm"`
	Event        types.APIEvent                        `json:"event"`
	Handler      types.SlashHandler                    `json:"-"`
	SlashOptions []*discordgo.ApplicationCommandOption `json:"slash_options"` // Slash command options
	Disabled     bool                                  `json:"disabled"`
	Server       string                                `json:"server"`
}
