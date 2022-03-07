function getBotId(id) {
    return document.querySelector(id+"-alt").value || document.querySelector(id).value
}

async function claim() {
    let botId = getBotId("#queue")
    let res = await fetch(`/bot-actions/claim?csrf_token=${csrfToken}`, {
        method: "POST",
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"bot_id": botId}),
    })
    let json = await res.json()
    alert(json.detail)
}

async function unclaim() {
    let botId = getBotId("#under_review_claim")
    let reason = document.querySelector("#under_review_claim-reason").value
    let res = await fetch(`/bot-actions/unclaim?csrf_token=${csrfToken}`, {
        method: "POST",
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"bot_id": botId, "reason": reason}),
    })
    let json = await res.json()
    alert(json.detail)
}

async function approve() {
    let botId = getBotId("#under_review_approved")
    let reason = document.querySelector("#under_review_approved-reason").value
    let res = await fetch(`/bot-actions/approve?csrf_token=${csrfToken}`, {
        method: "POST",
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"bot_id": botId, "reason": reason}),
    })
    let json = await res.json()
    alert(json.detail)
    if(res.ok) {
        // Now put the invite to the bot
        window.location.href = `https://discord.com/api/oauth2/authorize?client_id=${botId}&scope=bot&application.command&guild_id=${json.guild_id}`
    }
}

async function deny() {
    let botId = getBotId("#under_review_denied")
    let reason = document.querySelector("#under_review_denied-reason").value
    let res = await fetch(`/bot-actions/deny?csrf_token=${csrfToken}`, {
        method: "POST",
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"bot_id": botId, "reason": reason}),
    })
    let json = await res.json()
    alert(json.detail)
}

async function ban() {
    let botId = getBotId("#ban")
    let reason = document.querySelector("#ban-reason").value
    let res = await fetch(`/bot-actions/ban?csrf_token=${csrfToken}`, {
        method: "POST",
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"bot_id": botId, "reason": reason}),
    })
    let json = await res.json()
    alert(json.detail)
}

async function unban() {
    let botId = getBotId("#unban")
    let reason = document.querySelector("#unban-reason").value
    let res = await fetch(`/bot-actions/unban?csrf_token=${csrfToken}`, {
        method: "POST",
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"bot_id": botId, "reason": reason}),
    })
    let json = await res.json()
    alert(json.detail)
}

async function certify() {
    let botId = getBotId("#certify")
    let reason = document.querySelector("#certify-reason").value
    let res = await fetch(`/bot-actions/certify?csrf_token=${csrfToken}`, {
        method: "POST",
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"bot_id": botId, "reason": reason}),
    })
    let json = await res.json()
    alert(json.detail)
}

async function uncertify() {
    let botId = getBotId("#uncertify")
    let reason = document.querySelector("#uncertify-reason").value
    let res = await fetch(`/bot-actions/uncertify?csrf_token=${csrfToken}`, {
        method: "POST",
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"bot_id": botId, "reason": reason}),
    })
    let json = await res.json()
    alert(json.detail)
}

async function unverify() {
    let botId = getBotId("#unverify")
    let reason = document.querySelector("#unverify-reason").value
    let res = await fetch(`/bot-actions/unverify?csrf_token=${csrfToken}`, {
        method: "POST",
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"bot_id": botId, "reason": reason}),
    })
    let json = await res.json()
    alert(json.detail)
}

async function requeue() {
    let botId = getBotId("#requeue")
    let reason = document.querySelector("#requeue-reason").value
    let res = await fetch(`/bot-actions/requeue?csrf_token=${csrfToken}`, {
        method: "POST",
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"bot_id": botId, "reason": reason}),
    })
    let json = await res.json()
    alert(json.detail)
}

async function resetVotes() {
    let botId = getBotId("#reset-votes")
    let reason = document.querySelector("#reset-votes-reason").value
    let res = await fetch(`/bot-actions/reset-votes?csrf_token=${csrfToken}`, {
        method: "POST",
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"bot_id": botId, "reason": reason}),
    })
    let json = await res.json()
    alert(json.detail)
}

async function setFlag() {
    let botId = getBotId("#set-flag")
    let reason = document.querySelector("#set-flag-reason").value
    let flag = parseInt(document.querySelector("#flag").value)

    let url = "/bot-actions/set-flag"

    if(document.querySelector("#unset").checked) {
        url = "/bot-actions/unset-flag"
    }

    let res = await fetch(`${url}?csrf_token=${csrfToken}`, {
        method: "POST",
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({"bot_id": botId, "reason": reason, "context": flag}),
    })
    let json = await res.json()
    alert(json.detail)
}
