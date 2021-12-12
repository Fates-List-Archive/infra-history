package slashbot

import (
	"context"
	"dragon/common"
	"dragon/types"
	"errors"
	"math"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/Fates-List/discordgo"
	"github.com/davecgh/go-spew/spew"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

var (
	iResponseMap     map[string]*time.Timer        = make(map[string]*time.Timer, 0) // Interaction response map to check if interaction has been responded to
	commandNameCache map[string]string             = make(map[string]string)
	commands         map[string]types.SlashCommand = make(map[string]types.SlashCommand)
	mockGuild        string                        // The guild to mock if set
	mockUser         string                        // The user to mock if set
)

func SetupSlash(discord *discordgo.Session, cmdInit types.SlashFunction) {
	commandsIr := cmdInit()

	var cmds []*discordgo.ApplicationCommand

	// Add the slash commands
	for cmdName, cmdData := range commandsIr {
		var v types.SlashCommand = cmdData

		if v.Disabled {
			continue
		}

		commandNameCache[v.Name] = cmdName

		cmd := discordgo.ApplicationCommand{
			Name:        v.Name,
			Description: v.Description,
			Options:     v.Options,
		}

		if common.RegisterCommands {
			log.Info("Adding slash command: ", cmdName+" with server of "+v.Server)
		} else {
			log.Info("Loading slash command " + cmdName + " with server of " + v.Server)
		}

		if v.Server == "" {
			cmds = append(cmds, &cmd)
		} else {
			go func() {
				if common.RegisterCommands {
					_, err := discord.ApplicationCommandCreate(discord.State.User.ID, v.Server, &cmd)
					time.Sleep(1 * time.Second)
					log.Info(v.Autocompleter)
					if v.Server == common.StaffServer {
						go discord.ApplicationCommandCreate(discord.State.User.ID, common.StaffServer, &cmd) // Just to force create
					}
					if err != nil {
						panic(err.Error())
						return
					}
				}
			}()
		}
		commands[discord.State.User.ID+cmdName] = cmdData
	}

	log.Info("Loading commands on Discord for ", discord.State.User.Username)
	if common.RegisterCommands {
		_, err := discord.ApplicationCommandBulkOverwrite(discord.State.User.ID, "", cmds)
		if err != nil {
			log.Fatal("Cannot create commands due to error: ", err)
		}
		go discord.ApplicationCommandBulkOverwrite(discord.State.User.ID, common.StaffServer, cmds)
	}
	log.Info("All slash commands for server list loaded!")

	if common.RegisterCommands {
		apps, _ := discord.ApplicationCommands(discord.State.User.ID, common.StaffServer)
		log.Info(spew.Sdump(apps))
		time.AfterFunc(3*time.Second, func() { os.Exit(0) })
	}
}

func SlashHandler(
	ctx context.Context,
	discord *discordgo.Session,
	rdb *redis.Client,
	db *pgxpool.Pool,
	i *discordgo.InteractionCreate,
) {
	if i.Type != discordgo.InteractionApplicationCommand && i.Type != discordgo.InteractionApplicationCommandAutocomplete {
		// Not yet supported
		return
	}

	var appCmdData = i.ApplicationCommandData()

	if i.Interaction.Member == nil {
		SendIResponse(discord, i.Interaction, "This bot may only be used in a server!", true)
		return
	}

	if appCmdData.Name == "mock" && i.Type == discordgo.InteractionApplicationCommand {
		// Special command to mock all other commands
		if i.Interaction.GuildID != common.StaffServer {
			return
		}

		_, isStaff, _ := common.GetPerms(common.DiscordMain, ctx, i.Interaction.Member.User.ID, 4)
		if !isStaff {
			SendIResponse(discord, i.Interaction, "You are not a Fates List Admin. If you think this is a mistake, please report this on FL Kremlin!", true)
			return
		}
		guildVal := GetArg(discord, i.Interaction, "guild", true)
		guildIdVal, ok := guildVal.(string)
		var msg string
		if !ok || guildIdVal == "" {
			mockGuild = ""
			mockUser = ""
			msg = "Mock mode disabled"
		} else {
			mockGuild = guildIdVal
			mockUser = i.Interaction.Member.User.ID
			msg = "Mock mode enabled and set to " + guildIdVal
		}
		SendIResponse(discord, i.Interaction, msg, true)
		return
	} else if mockGuild != "" && mockUser == i.Interaction.Member.User.ID {
		i.Interaction.GuildID = mockGuild
	}

	var op string = commandNameCache[appCmdData.Name]

	if op == "" {
		return
	}

	cmd := commands[discord.State.User.ID+op]

	if cmd.Server != "" && cmd.Server != i.Interaction.GuildID {
		SendIResponse(discord, i.Interaction, "This command may not be run on this server", true)
		return
	}

	handlerData := types.HandlerData{
		Context:     context.Background(),
		Discord:     discord,
		Postgres:    db,
		Redis:       rdb,
		Interaction: i.Interaction,
		AppCmdData:  appCmdData,
		Index:       cmd.Index,
	}

	switch i.Type {
	case discordgo.InteractionApplicationCommand:
		// Deferring only works for application commands
		timeout := time.AfterFunc(time.Second*2, func() {
			SendIResponse(discord, i.Interaction, "defer", false)
		})

		defer timeout.Stop()

		// Handle cooldown
		if cmd.Cooldown != types.CooldownNone {
			key := "cooldown-" + cmd.Cooldown.InternalName + "-" + i.Interaction.Member.User.ID
			cooldown, err := rdb.TTL(ctx, key).Result() // Format: cooldown-BUCKET-MOD
			if err == nil && cooldown.Seconds() > 0 {
				SendIResponse(discord, i.Interaction, "Please wait "+cooldown.String()+" before retrying this command!", true)
				return
			}
			rdb.Set(ctx, key, "0", time.Duration(cmd.Cooldown.Time)*time.Second)
		}

		if cmd.Handler == nil {
			SendIResponse(discord, i.Interaction, "Command not found?", false)
			return
		}
		res := cmd.Handler(handlerData)

		if res != "" && !strings.HasPrefix(res, "nop") {
			SendIResponse(discord, i.Interaction, res, true)
		}
	case discordgo.InteractionApplicationCommandAutocomplete:
		// Simple autocompletion code
		if cmd.Autocompleter == nil {
			SendIResponse(discord, i.Interaction, "nop", true)
			return
		}
		choices := cmd.Autocompleter(handlerData)
		if len(choices) <= 0 {
			choices = []*discordgo.ApplicationCommandOptionChoice{}
		}
		discord.InteractionRespond(i.Interaction, &discordgo.InteractionResponse{
			Type: discordgo.InteractionApplicationCommandAutocompleteResult,
			Data: &discordgo.InteractionResponseData{
				Choices: choices,
			},
		})
	}
	go func() {
		if iResponseMap[i.Interaction.Token] != nil {
			iResponseMap[i.Interaction.Token].Stop()
		}
		delete(iResponseMap, i.Interaction.Token)
	}() // This tends to be a bit slow
}

func CheckServerPerms(discord *discordgo.Session, i *discordgo.Interaction, permNum int) bool {
	if mockGuild == i.GuildID && mockUser == i.Member.User.ID {
		return true
	}
	var perm int64
	var permStr string
	switch permNum {
	case 1:
		perm = discordgo.PermissionSendMessages
		permStr = "Send Messages"
	case 2:
		perm = discordgo.PermissionManageServer
		permStr = "Manage Server or Administrator"
	case 3:
		perm = discordgo.PermissionAdministrator
		permStr = "Administrator"
	default:
		perm = discordgo.PermissionAdministrator
		permStr = "Administrator"
	}
	if i.Member.Permissions&perm == 0 {
		SendIResponse(discord, i, "You need "+permStr+" in order to use this command", true)
		return false
	}

	if permNum >= 4 {
		ok, is_staff, perm := common.GetPerms(discord, context.Background(), i.Member.User.ID, float32(permNum+1))
		if ok != "" {
			SendIResponse(discord, i, "Something went wrong while verifying your identity!", true)
			return false
		}
		if !is_staff {
			SendIResponse(discord, i, "This operation requires perm: "+strconv.Itoa(int(permNum+1))+" but you only have perm number "+strconv.Itoa(int(perm))+".", true)
			return false
		}
	}
	return true
}

func SendIResponse(discord *discordgo.Session, i *discordgo.Interaction, content string, clean bool, largeContent ...string) {
	sendIResponseComplex(discord, i, content, clean, 0, largeContent, nil, 0)
}

func SendIResponseEphemeral(discord *discordgo.Session, i *discordgo.Interaction, content string, clean bool, largeContent ...string) {
	sendIResponseComplex(discord, i, content, clean, 1<<6, largeContent, nil, 0)
}

func sendIResponseComplex(discord *discordgo.Session, i *discordgo.Interaction, content string, clean bool, flags uint64, largeContent []string, embeds []*discordgo.MessageEmbed, tries int) {
	// Sends a response to a interaction using iResponseMap as followup if needed. If clean is set, iResponseMap is cleaned out
	if len(content) > 2000 {
		log.Info("Sending large content of length: " + strconv.Itoa(len(content)))
		var offset int = 0
		pos := [2]int{0, 2000}
		countedChars := 0
		sendIResponseComplex(discord, i, "defer", clean, flags, []string{}, embeds, 0)
		for countedChars < len(content) {
			sendIResponseComplex(discord, i, content[pos[0]:pos[1]], clean, flags, []string{}, embeds, 0)

			// Switch {0, 2000} to {2000, XYZ}
			offset = int(math.Min(2000, float64(len(content)-pos[0]))) // Find new offset to use
			pos[0] += offset
			countedChars += 2000
			pos[1] += int(math.Min(2000, float64(len(content)-countedChars)))
		}

		if len(largeContent) == 0 {
			content = "nop"
		} else {
			content = "Attachments:"
		}
	}

	var files []*discordgo.File
	for i, data := range largeContent {
		files = append(files, &discordgo.File{
			Name:        "output" + strconv.Itoa(i) + ".txt",
			ContentType: "application/text",
			Reader:      strings.NewReader(data),
		})
	}

	t, ok := iResponseMap[i.Token]
	if ok && content != "nop" {
		_, err := discord.FollowupMessageCreate(discord.State.User.ID, i, true, &discordgo.WebhookParams{
			Content: content,
			Flags:   flags,
			Files:   files,
			Embeds:  embeds,
		})
		if err != nil {
			log.Error(err.Error())
		}
	} else if content != "nop" {
		var err error
		if content != "defer" {
			err = discord.InteractionRespond(i, &discordgo.InteractionResponse{
				Type: discordgo.InteractionResponseChannelMessageWithSource,
				Data: &discordgo.InteractionResponseData{
					Content: content,
					Flags:   flags,
					Files:   files,
					Embeds:  embeds,
				},
			})
		} else {
			err = errors.New("deferring response due to timeout or requested defer...")
		}
		if err != nil {
			if content != "defer" {
				log.Error("An error has occurred in initial response: " + err.Error())
			}
			err := discord.InteractionRespond(i, &discordgo.InteractionResponse{
				Type: discordgo.InteractionResponseDeferredChannelMessageWithSource,
				Data: &discordgo.InteractionResponseData{
					Flags: flags,
				},
			})
			if err != nil {
				log.Error(err)
				sendIResponseComplex(discord, i, "Something happened!\nError: "+err.Error(), false, flags, []string{}, nil, 0)
			}
		}
	}

	if clean {
		if ok && t != nil {
			t.Stop()
		}
		delete(iResponseMap, i.Token)
	} else {
		if !ok {
			iResponseMap[i.Token] = time.AfterFunc(15*time.Minute, func() {
				delete(iResponseMap, i.Token)
			})
		}
	}
}

func recovery() {
	err := recover()
	if err != nil {
		log.Error(err)
	}
}

func GetArg(discord *discordgo.Session, i *discordgo.Interaction, name string, possibleLink bool) interface{} {
	// Gets an argument, if possibleLink is set, this will convert the possible link using common/converters.go if possible
	defer recovery()
	appCmdData := i.ApplicationCommandData()
	for _, v := range appCmdData.Options {
		if v.Name == name {
			if v.Type == discordgo.ApplicationCommandOptionString {
				sVal := strings.TrimSpace(v.StringValue())
				if possibleLink {
					return common.RenderPossibleLink(sVal)
				}
				return sVal
			} else if v.Type == discordgo.ApplicationCommandOptionInteger {
				return v.IntValue()
			} else if v.Type == discordgo.ApplicationCommandOptionBoolean {
				return v.BoolValue()
			} else if v.Type == discordgo.ApplicationCommandOptionUser {
				return v.UserValue(discord)
			} else if v.Type == discordgo.ApplicationCommandOptionChannel {
				return v.ChannelValue(discord)
			}
		}
	}
	return nil
}
