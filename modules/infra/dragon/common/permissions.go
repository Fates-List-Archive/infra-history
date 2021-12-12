package common

import (
	"dragon/types"
	"encoding/json"
	"io/ioutil"

	"github.com/Fates-List/discordgo"
	"github.com/google/uuid"
	log "github.com/sirupsen/logrus"
)

var staffRoleCache = make(map[string]string)
var StaffRoles types.StaffRoles
var staffRoleFilePath string

func permInit() {
	var staffRoleFile, ferr = ioutil.ReadFile(staffRoleFilePath)

	if ferr != nil {
		panic(ferr.Error())
	}

	err := json.Unmarshal(staffRoleFile, &StaffRoles)

	if err != nil {
		panic(err.Error())
	}

	// Create role cache
	for key, element := range StaffRoles {
		staffRoleCache[element.ID] = key
	}
}

func CreateUUID() string {
	uuid, err := uuid.NewRandom()
	if err != nil || uuid.String() == "" {
		return CreateUUID()
	}
	return uuid.String()
}

func GetUserPerms(roles []string) types.StaffRole {
	var maxPerm types.StaffRole = StaffRoles["user"]
	var potPerm types.StaffRole
	if len(roles) == 0 {
		return maxPerm
	}

	for _, role := range roles {
		if val, ok := staffRoleCache[role]; ok {
			potPerm = StaffRoles[val]
			if potPerm.Perm > maxPerm.Perm {
				maxPerm = potPerm
			}
		}
	}
	return maxPerm
}

func GetPerms(discord *discordgo.Session, user_id string, min_perm float32) (role types.StaffRole, is_staff bool, perm float32) {
	perms := StaffRoles["user"]
	member, err := discord.State.Member(MainServer, user_id)
	if err != nil {
		log.Warn(err)
	} else {
		perms = GetUserPerms(member.Roles)
	}
	return perms, perms.Perm >= min_perm, perms.Perm
}
