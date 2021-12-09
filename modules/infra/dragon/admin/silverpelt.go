package admin

// silverpelt.go takes the information from ir.go, does validation checks, passes it to the commands handler and returns the output

import (
	"context"
	"dragon/common"
	"dragon/types"
	"encoding/json"
	"strconv"
	"time"

	"github.com/Fates-List/discordgo"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

func silverpelt(
	ctx context.Context,
	discord *discordgo.Session,
	interaction *discordgo.Interaction,
	rdb *redis.Client,
	db *pgxpool.Pool,
	user_id string,
	bot_id string,
	op string,
	admin_redis_context types.AdminRedisContext,
	originServer string,
) string {
	if admin_op, yes := commands[op]; yes {
		ok, is_staff, perm := common.GetPerms(discord, ctx, user_id, float32(admin_op.MinimumPerm))
		if ok != "" {
			return "Something went wrong!"
		}

		if admin_op.Server != "" && admin_op.Server != originServer && admin_op.InternalName != "mock" {
			return "Please exit mock mode and try again!"
		}

		if !is_staff {
			return "This operation requires perm: " + strconv.Itoa(int(admin_op.MinimumPerm)) + " but you only have perm number " + strconv.Itoa(int(perm)) + ".\nUser ID: " + user_id
		}

		if admin_op.ReasonNeeded && len(admin_redis_context.Reason) < 3 {
			return "You must specify a reason for doing this!"
		}

		var state pgtype.Int4
		var owner pgtype.Int8
		db.QueryRow(ctx, "SELECT state FROM bots WHERE bot_id = $1", bot_id).Scan(&state)

		if bot_id == "" {
			state = pgtype.Int4{Status: pgtype.Present}
		}

		if state.Status != pgtype.Present {
			return "This bot does not exist!"
		}

		db.QueryRow(ctx, "SELECT owner FROM bot_owner WHERE bot_id = $1 AND main = true", bot_id).Scan(&owner)

		if owner.Status != pgtype.Present && bot_id != "" {
			db.Exec(ctx, "DELETE FROM bot_owner WHERE bot_id = $1", bot_id)
			db.Exec(ctx, "INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, true)", bot_id, user_id)
			err := db.QueryRow(ctx, "SELECT owner FROM bot_owner WHERE bot_id = $1 AND main = true", bot_id).Scan(&owner)

			if err != nil {
				return err.Error()
			}

			return "This bot does not have a main owner. You have temporarily been given main owner as a result"
		}

		log.Warn("Bot owner: ", owner.Int)

		state_data := types.GetBotState(int(state.Int))

		member, err := discord.State.Member(common.MainServer, user_id)

		if err != nil {
			log.Warn(err)
			return "You were not found in the main server somehow. Try again later"
		}

		var bot_m *discordgo.Member
		var errm error

		if bot_id != "" {
			bot_m, errm = discord.State.Member(common.MainServer, bot_id)
		} else {
			bot_m, errm = member, nil
		}

		var bot *discordgo.User
		if errm != nil {
			bot, err = discord.User(bot_id)
			if err != nil {
				return "This bot could not be found anywhere..."
			}
		} else {
			bot = bot_m.User
		}

		context := types.AdminContext{
			Context:      ctx,
			Discord:      discord,
			Interaction:  interaction,
			Postgres:     db,
			Redis:        rdb,
			User:         member.User,
			Bot:          bot,
			BotState:     state_data,
			Reason:       admin_redis_context.Reason,
			ExtraContext: admin_redis_context.ExtraContext,
			Owner:        strconv.FormatInt(owner.Int, 10),
		}

		if context.Reason == "" && !admin_op.SlashRaw {
			reason := "No reason specified"
			context.Reason = reason
		}

		op_err := admin_op.Handler(context)

		if op_err == "" && admin_op.Event != types.EventNone {
			eventId := common.CreateUUID()
			event := types.Event{
				Context: types.SimpleContext{
					User:   context.User.ID,
					Reason: &context.Reason,
				},
				Metadata: types.EventMetadata{
					Event:     admin_op.Event,
					User:      context.User.ID,
					Timestamp: float64(time.Now().Second()),
					EventId:   eventId,
					EventType: -1,
				},
			}
			// Add event
			_, err = db.Exec(ctx, "INSERT INTO bot_api_event (bot_id, event, type, context, id) VALUES ($1, $2, $3, $4, $5)", bot_id, admin_op.Event, -1, event, eventId)

			if err != nil {
				log.Warning(err)
			}

			ok, webhookType, secret, webhookURL := common.GetWebhook(ctx, "bots", bot_id, db)
			if ok && webhookType == types.FatesWebhook {
				event_str, err := json.Marshal(event)
				if err != nil {
					log.Error(err)
				} else {
					_ = common.WebhookReq(ctx, db, eventId, webhookURL, secret, string(event_str), 0)
				}
			}
		}

		if op_err != "" {
			op_err += "\nCurrent State: " + state_data.Str() + "\nBot owner: " + strconv.FormatInt(owner.Int, 10)
		} else {
			op_err = "OK."
		}

		return op_err
	} else {
		return "This bot operation does not exist (" + op + ")."
	}
}

func CommandsToJSON() (ok bool, json_data []byte) {
	json_data, err := json.Marshal(commands)
	if err != nil {
		log.Warn(err)
		return false, nil
	}
	return true, json_data
}
