package common

import (
	"errors"
	"io"
	"math/rand"
	"net/http"
	"time"

	"github.com/Fates-List/discordgo"
)

var reqCounter int

var ErrJAPIRequestLimit = errors.New("Too many requests")

func rng(min int, max int) int {
	rand.Seed(time.Now().UnixNano())
	return rand.Intn(max-min+1) + min
}

func randWait() int {
	return rng(0, 1)
}

// Unused right now, but fetches a user
func JAPIFetchUser(userID string, wait bool) (map[string]any, error) {
	if reqCounter > 60 {
		if !wait {
			return nil, ErrJAPIRequestLimit
		} else {
			time.Sleep(3 * time.Minute)
		}
	}

	// Extra wait to make it seem like a normal user
	time.Sleep(time.Duration(randWait()) * time.Second)

	client := http.Client{Timeout: 15 * time.Second}
	gcReq, err := http.NewRequest("GET", "https://japi.rest/discord/v1/user/"+userID, nil)
	if err != nil {
		return nil, err
	}
	gcReq.Header.Add("Authorization", JAPIKey)

	reqCounter++ // Increment request counter

	gcResp, err := client.Do(gcReq)

	if err != nil {
		return nil, err
	}

	if gcResp.StatusCode != 200 {
		return nil, errors.New("japi.rest returned a non-success status code when getting the approximate guild count. Please report this error to skylar#6666 if this happens after retrying!\n\n" + gcResp.Status)
	}
	defer gcResp.Body.Close()

	body, err := io.ReadAll(gcResp.Body)
	if err != nil {
		return nil, err
	}
	var jMap map[string]any
	err = json.Unmarshal(body, &jMap)
	return jMap, err
}

// Fetch user from either a random bot or japi.rest using RNG
// with more focus towards bots. This assumes not in state
func FetchUserRNG(userID string) (user *discordgo.User, err error, t string) {
	// Randomly choose between JAPI and bot
	rngVal := rng(0, 5)
	if rngVal > 3 {
		// JAPI
		japiUser, err := JAPIFetchUser(userID, false)
		if err == ErrJAPIRequestLimit {
			// Do nothing, passthrough
		} else if err != nil {
			return nil, err, "unknown"
		} else {
			data, ok := japiUser["data"].(map[string]any)
			if ok {
				bot, ok := data["bot"].(bool)
				if !ok {
					bot = false
				}
				username, ok := data["username"].(string)
				if !ok {
					username = "Unknown"
				}

				disc, ok := data["discriminator"].(string)
				if !ok {
					disc = "0000"
				}

				avatar, ok := data["avatar"].(string)
				if !ok {
					avatar = ""
				}

				return &discordgo.User{
					ID:            userID,
					Username:      username,
					Discriminator: disc,
					Avatar:        avatar,
					Bot:           bot,
				}, nil, "japi"
			}
		}
	}

	// Randomly choose a bot if JAPI fails
	bots := []*discordgo.Session{DiscordMain, DiscordServerList, fetchBot1}
	rngVal = rng(1, len(bots))
	bot := bots[rngVal-1]
	user, err = bot.User(userID)
	return user, err, "bot"
}
