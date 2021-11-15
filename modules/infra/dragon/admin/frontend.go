// Frontend code
package admin

import (
	"context"
	"dragon/common"
	"dragon/types"
	"encoding/json"
	"strconv"
	"time"

	"github.com/bwmarrin/discordgo"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

func AdminOp(
	ctx context.Context,
	discord *discordgo.Session,
	rdb *redis.Client,
	db *pgxpool.Pool,
	user_id string,
	bot_id string,
	op string,
	admin_redis_context types.AdminRedisContext,
) string {
	if admin_op, yes := commands[op]; yes {
		ok, is_staff, perm := common.GetPerms(discord, ctx, user_id, float32(admin_op.MinimumPerm))
		if ok != "" {
			return "Something went wrong!"
		}

		if !is_staff {
			return "This operation requires perm: " + strconv.Itoa(int(admin_op.MinimumPerm)) + " but you only have perm number " + strconv.Itoa(int(perm)) + ".\nUser ID: " + user_id
		}

		if admin_op.ReasonNeeded && (admin_redis_context.Reason == nil || len(*admin_redis_context.Reason) < 3) {
			return "You must specify a reason for doing this!"
		}

		if admin_op.Cooldown != types.CooldownNone {
			key := "cooldown-" + admin_op.Cooldown.InternalName + "-" + user_id
			cooldown, err := rdb.TTL(ctx, key).Result() // Format: cooldown-BUCKET-MOD
			if err == nil && cooldown.Seconds() > 0 {
				return "Please wait " + cooldown.String() + " before retrying this operation!"
			}
			rdb.Set(ctx, key, "0", time.Duration(admin_op.Cooldown.Time)*time.Second)
		}

		if bot_id == "0" && !admin_op.Recursive {
			return "This operation is not recursive. You must provide a nonzero Bot ID"
		}

		var state pgtype.Int4
		var owner pgtype.Int8
		db.QueryRow(ctx, "SELECT state FROM bots WHERE bot_id = $1", bot_id).Scan(&state)

		if state.Status != pgtype.Present {
			return "This bot does not exist!"
		}

		db.QueryRow(ctx, "SELECT owner FROM bot_owner WHERE bot_id = $1 AND main = true", bot_id).Scan(&owner)

		if owner.Status != pgtype.Present {
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

		bot_m, err := discord.State.Member(common.MainServer, bot_id)

		var bot *discordgo.User
		if err != nil {
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
			Postgres:     db,
			Redis:        rdb,
			User:         member.User,
			Bot:          bot,
			BotState:     state_data,
			Reason:       admin_redis_context.Reason,
			ExtraContext: admin_redis_context.ExtraContext,
			Owner:        strconv.FormatInt(owner.Int, 10),
		}

		if context.Reason == nil {
			reason := "No reason specified"
			context.Reason = &reason
		}

		op_err := admin_op.Handler(context)

		if op_err == "" && admin_op.Event != types.EventNone {
			eventId := common.CreateUUID()
			event := types.Event{
				Context: types.SimpleContext{
					User:   context.User.ID,
					Reason: context.Reason,
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
