package slashbot

import (
	"context"
	"dragon/common"
	"dragon/types"
	"errors"
	"math"
	"strconv"
	"strings"
	"time"

	"github.com/Fates-List/discordgo"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

var (
	iResponseMap     map[string]*time.Timer        = make(map[string]*time.Timer, 0) // Interaction response map to check if interaction has been responded to
	commandNameCache map[string]string             = make(map[string]string)
	commands         map[string]types.SlashCommand = make(map[string]types.SlashCommand)
)

func SetupSlash(discord *discordgo.Session, cmdInit types.SlashFunction) {
	commandsIr := cmdInit()

	var cmds []*discordgo.ApplicationCommand

	// Add the slash commands
	for cmdName, cmdData := range commandsIr {
		var v types.SlashCommand = cmdData

		for v.Alias != "" {
			log.Info("Resolving alias " + cmdName)
			v = commands[cmdData.Alias]
			oldName := v.Name
			v.Name = cmdData.Name
			if cmdData.Description != "" {
				v.Description = cmdData.Description
			} else {
				v.Description += ". Alias to /" + oldName
			}
		}

		if v.Disabled {
			continue
		}

		commandNameCache[v.Name] = cmdName

		cmd := discordgo.ApplicationCommand{
			Name:        v.Name,
			Description: v.Description,
			Options:     v.Options,
		}
		log.Info("Adding slash command: ", cmdName+" with server of "+v.Server)

		if v.Server == "" {
			cmds = append(cmds, &cmd)
		} else {
			go func() {
				_, err := discord.ApplicationCommandCreate(discord.State.User.ID, v.Server, &cmd)
				if v.Server == common.StaffServer {
					go discord.ApplicationCommandCreate(discord.State.User.ID, common.StaffServer, &cmd) // Just to force create
				}
				if err != nil {
					panic(err.Error())
					return
				}
			}()
		}
		commands[discord.State.User.ID+cmdName] = cmdData
	}

	log.Info("Loading commands on Discord for ", discord.State.User.Username)
	_, err := discord.ApplicationCommandBulkOverwrite(discord.State.User.ID, "", cmds)
	if err != nil {
		log.Fatal("Cannot create commands due to error: ", err)
	}
	go discord.ApplicationCommandBulkOverwrite(discord.State.User.ID, common.StaffServer, cmds)
	log.Info("All slash commands for server list loaded!")
}

func SlashHandler(
	ctx context.Context,
	discord *discordgo.Session,
	rdb *redis.Client,
	db *pgxpool.Pool,
	i *discordgo.InteractionCreate,
) {
	var appCmdData = i.ApplicationCommandData()

	var op string = commandNameCache[appCmdData.Name]

	if op == "" {
		return
	}

	if i.Interaction.Member == nil {
		SendIResponse(discord, i.Interaction, "This bot may only be used in a server!", true)
		return
	}

	cmd := commands[discord.State.User.ID+op]

	if cmd.Server != "" && cmd.Server != i.Interaction.GuildID {
		SendIResponse(discord, i.Interaction, "This command may not be run on this server", true)
		return
	}

	for cmd.Alias != "" {
		cmd = commands[cmd.Alias]
	}

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

	timeout := time.AfterFunc(time.Second*2, func() {
		SendIResponse(discord, i.Interaction, "defer", false)
	})
	defer timeout.Stop()

	res := cmd.Handler(discord, db, rdb, i.Interaction, appCmdData, cmd.Index)

	if res != "" {
		SendIResponse(discord, i.Interaction, res, true)
	}
	if iResponseMap[i.Interaction.Token] != nil {
		iResponseMap[i.Interaction.Token].Stop()
	}
	delete(iResponseMap, i.Interaction.Token)
}

func CheckServerPerms(discord *discordgo.Session, i *discordgo.Interaction, permNum int) bool {
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
	sendIResponseComplex(discord, i, content, clean, 0, largeContent, 0)
}

func SendIResponseEphemeral(discord *discordgo.Session, i *discordgo.Interaction, content string, clean bool, largeContent ...string) {
	sendIResponseComplex(discord, i, content, clean, 1<<6, largeContent, 0)
}

func sendIResponseComplex(discord *discordgo.Session, i *discordgo.Interaction, content string, clean bool, flags uint64, largeContent []string, tries int) {
	// Sends a response to a interaction using iResponseMap as followup if needed. If clean is set, iResponseMap is cleaned out
	if len(content) > 2000 {
		log.Info("Sending large content of length: " + strconv.Itoa(len(content)))
		var offset int = 0
		pos := [2]int{0, 2000}
		countedChars := 0
		sendIResponseComplex(discord, i, "defer", clean, flags, []string{}, 0)
		for countedChars < len(content) {
			sendIResponseComplex(discord, i, content[pos[0]:pos[1]], clean, flags, []string{}, 0)

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
				sendIResponseComplex(discord, i, "Something happened!\nError: "+err.Error(), false, flags, []string{}, 0)
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
