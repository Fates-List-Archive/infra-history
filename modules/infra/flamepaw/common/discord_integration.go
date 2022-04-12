package common

import (
	"strconv"
	"strings"

	"github.com/bwmarrin/discordgo"
	log "github.com/sirupsen/logrus"
)

func SendIntegration(discord *discordgo.Session, userId string, botId string, webhookURL string, voteCount int) {
	if !strings.HasPrefix(webhookURL, "https://discord.com/api/webhooks") {
		log.WithFields(log.Fields{
			"url": webhookURL,
		}).Warning("Invalid webhook URL")
	}
	parts := strings.Split(webhookURL, "/")
	if len(parts) < 7 {
		log.WithFields(log.Fields{
			"url": webhookURL,
		}).Warning("Invalid webhook URL")
		return
	}
	webhookId := parts[5]
	webhookToken := parts[6]
	userObj, err := discord.User(userId)
	if err != nil {
		log.WithFields(log.Fields{
			"user": userId,
		}).Warning(err)
	}

	botObj, err := discord.User(botId)
	if err != nil {
		log.WithFields(log.Fields{
			"user": botId,
		}).Warning(err)
	}

	userWithDisc := userObj.Username + "#" + userObj.Discriminator

	_, err = discord.WebhookExecute(webhookId, webhookToken, true, &discordgo.WebhookParams{
		Username: "Fates List - " + userWithDisc + " (" + userObj.ID + ")",
		Embeds: []*discordgo.MessageEmbed{
			{
				Title:       "New Vote on Fates List",
				Description: userWithDisc + " with ID " + userObj.ID + " has just cast a vote for " + botObj.Username + " with ID " + botObj.ID + " on Fates List!\nIt now has " + strconv.Itoa(voteCount) + " votes!\n\nThank you for supporting this bot\n**GG**",
				Color:       242424,
			},
		},
	})
}
