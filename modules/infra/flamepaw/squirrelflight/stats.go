package squirrelflight

import (
	"flamepaw/common"

	"github.com/Fates-List/discordgo"
	log "github.com/sirupsen/logrus"
)

func SendStats() {
	msgs, err := common.DiscordSquirrelflight.ChannelMessages(common.StatsChannel, 100, "", "", "")
	if err != nil {
		log.Error(err)
	}
	msgList := []string{}
	for _, msg := range msgs {
		if msg.Author.ID != common.DiscordSquirrelflight.State.User.ID {
			continue
		}
		msgList = append(msgList, msg.ID)
	}
	common.DiscordSquirrelflight.ChannelMessagesBulkDelete(common.StatsChannel, msgList)

	_, err = common.DiscordSquirrelflight.ChannelMessageSendComplex(common.StatsChannel, &discordgo.MessageSend{
		Content: "",
		Embed: &discordgo.MessageEmbed{
			URL:   "https://fateslist.xyz/frostpaw/stats",
			Title: "Check out our statistics",
			Color: 0x00ff00,
		},
	})

	if err != nil {
		log.Error(err)
	}
}
