package admin

import (
	"github.com/Fates-List/discordgo"
)

var botWhitelist map[string]bool

// Silverpelt staff server protection (No longer used due to Flamepaw server merge)
func SilverpeltStaffServerProtect(discord *discordgo.Session, userID string) {
	//check, ok := botWhitelist[userID]
	//if !ok || !check {
	//	discord.GuildMemberDeleteWithReason(common.StaffServer, userID, "Unauthorized bot!")
	//}
}
