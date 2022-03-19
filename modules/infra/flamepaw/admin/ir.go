package admin

// ir.go handles the slash command IR and passes over the admin operation to silverpelt.go

import (
	"flamepaw/slashbot"
	"flamepaw/types"
)

// Prepend is complement to builtin append.
func Prepend[T any](items []T, item T) []T {
	return append([]T{item}, items...)
}

type irModalData struct {
	context types.SlashContext
	adminOp AdminOp
	botId   string
}

var contexts map[string]irModalData = make(map[string]irModalData)

func slashIr() map[string]types.SlashCommand {
	// Add the slash commands IR for use in slashbot. Is used internally by CmdInit

	var commandsToRet map[string]types.SlashCommand = make(map[string]types.SlashCommand)
	for cmdName, v := range commands {
		for key, handler := range v.ModalResponses {
			slashbot.AddModalHandler(key, handler)
		}

		commandsToRet[cmdName] = types.SlashCommand{
			CmdName:       cmdName,
			Name:          v.InternalName,
			Description:   v.Description,
			Cooldown:      v.Cooldown,
			Options:       v.SlashOptions,
			Server:        v.Server,
			Autocompleter: v.Autocompleter,
		}
	}
	return commandsToRet
}
