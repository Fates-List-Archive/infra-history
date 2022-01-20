package admin

import (
	"flamepaw/common"

	"github.com/Fates-List/discordgo"
)

var botWhitelist map[string]bool

// Silverpelt staff server protection
func SilverpeltStaffServerProtect(discord *discordgo.Session, userID string) {
	check, ok := botWhitelist[userID]
	if !ok || !check {
		discord.GuildMemberDeleteWithReason(common.StaffServer, userID, "Unauthorized bot!")
	}
}
