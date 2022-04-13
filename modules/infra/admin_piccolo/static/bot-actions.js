function getBotId(id) {
    return document.querySelector(id+"-alt").value || document.querySelector(id).value
}

function sendBotAction(name, botId, reason, context=null) {
    wsSend({
        request: "bot_action", 
        action: name, 
        action_data: {
            bot_id: botId, 
            reason: reason, 
            context: context
        }
    })
}

async function claim() {
    let botId = getBotId("#queue")
    sendBotAction("claim", botId, "STUB_REASON")
}

async function unclaim() {
    let botId = getBotId("#under_review_claim")
    let reason = document.querySelector("#under_review_claim-reason").value
    sendBotAction("unclaim", botId, reason)
}

async function approve() {
    let botId = getBotId("#under_review_approved")
    let reason = document.querySelector("#under_review_approved-reason").value
    sendBotAction("approve", botId, reason)
}

async function deny() {
    let botId = getBotId("#under_review_denied")
    let reason = document.querySelector("#under_review_denied-reason").value
    sendBotAction("deny", botId, reason)
}

async function ban() {
    let botId = getBotId("#ban")
    let reason = document.querySelector("#ban-reason").value
    sendBotAction("ban", botId, reason)
}

async function unban() {
    let botId = getBotId("#unban")
    let reason = document.querySelector("#unban-reason").value
    sendBotAction("unban", botId, reason)
}

async function certify() {
    let botId = getBotId("#certify")
    let reason = document.querySelector("#certify-reason").value
    sendBotAction("certify", botId, reason)
}

async function uncertify() {
    let botId = getBotId("#uncertify")
    let reason = document.querySelector("#uncertify-reason").value
    sendBotAction("uncertify", botId, reason)
}

async function unverify() {
    let botId = getBotId("#unverify")
    let reason = document.querySelector("#unverify-reason").value
    sendBotAction("unverify", botId, reason)
}

async function requeue() {
    let botId = getBotId("#requeue")
    let reason = document.querySelector("#requeue-reason").value
    sendBotAction("requeue", botId, reason)
}

async function resetVotes() {
    let botId = getBotId("#reset-votes")
    let reason = document.querySelector("#reset-votes-reason").value
    sendBotAction("reset-votes", botId, reason)
}

async function resetAllVotes() {
    let reason = document.querySelector("#reset-all-votes-reason").value || "STUB_REASON"
    sendBotAction("reset-all-votes", "0", reason)
}

async function setFlag() {
    let botId = getBotId("#set-flag")
    let reason = document.querySelector("#set-flag-reason").value
    let flag = parseInt(document.querySelector("#flag").value)

    let action = "set-flag"

    if(document.querySelector("#unset").checked) {
        action = "unset-flag"
    }

    sendBotAction(action, botId, reason, flag)
}

readyModule("bot-actions")