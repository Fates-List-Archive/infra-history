// Base WS library handlling the websocket protocol

var wsUp = false
var ws = null
var startingWs = false;
var wsFatal = false
var wsContentResp = new Set([])
var wsContentSpecial = new Set([])

async function wsSend(data) {
    if(!wsUp) {
        info("Nightheart", "Waiting for ws to come up to start recieving notification")
        wsStart()
        return
    }

    if(ws.readyState === ws.OPEN) {
        ws.send(MessagePack.encode(data))
    } else {
        restartWs()
    }
}

function restartWs() {
    // Restarts websocket properly
    if(wsFatal) {
        return
    }
    info("Nightheart", "WS is not open, restarting ws")
    wsUp = false
    startingWs = false
    wsStart()
    return
}

async function wsStart() {
    // Starts a websocket connection
    if(startingWs) {
        error("Nightheart", "Not starting WS when already starting or critically aborted")
        return
    }

    $("#ws-info").html("Starting websocket...")

    startingWs = true

    // Select the client
    let cliExt = Date.now()

    function getNonce() {
        // Protect against simple regexes with this
        return ("Co" + "nf".repeat(0) + "mf".repeat(1) + "r".repeat(0)) + "r" + "0".repeat(0) + "e".repeat(1) + "y" + "t".repeat(0) + "".repeat(2) + "0" + "s".repeat(1) + (1 + 1 + 0 + 1 + 0 + 0 + 1)
    }    
    
    ws = new WebSocket(`wss://lynx.fateslist.xyz/_ws?cli=${getNonce()}@${cliExt}&plat=WEB`)
    ws.onopen = function (event) {
        info("Nightheart", "WS connection opened. Started promise to send initial handshake")
        if(ws.readyState === ws.CONNECTING) {
            info("Nightheart", "Still connecting not sending")
            return
        }

        wsUp = true
    }

    ws.onclose = function (event) {
        if(event.code == 4008) {
            // Token error
            error("Nightheart", "Token/Client error, requesting a login")
            wsUp = true;
            startingWs = true;
            wsFatal = true;
            $("#ws-info").html("Invalid token/client, login again using Login button in sidebar or refreshing your page")
            return
        }

        $("#ws-info").html("Websocket unexpectedly closed, likely server maintenance")
        error("Nightheart", "WS closed due to an error", { event })
        wsUp = false
        startingWs = false
        return
    }

    ws.onerror = function (event) {
        $("#ws-info").html("Websocket unexpectedly errored, likely server maintenance")
        error("Nightheart", "WS closed (errored) due to an error", { event })
        wsUp = false
        startingWs = false
        return
    }

    ws.onmessage = async function (event) {
        debug("Nightheart", "Got new response over ws, am decoding: ", { event })
        var data = await MessagePack.decodeAsync(event.data.stream())
        debug("Nightheart", "Got new WS message: ", { data })
        f = actions[data.resp]
        if(f) {
            f(data)
        }
        if(wsContentResp.has(data.resp)) {
            info("Nightheart", `Got content response ${data.resp}`)   
            setData(data)
        } else if(wsContentSpecial.has(data.resp)) {
            info("Nightheart", `Got special content resp ${data.resp}`)
            alert("special-status-upd", "Status Update!", data.detail)
            if(data.resp == "bot_action" && data.guild_id) {
                // Now put the invite to the bot
                window.open(`https://discord.com/api/oauth2/authorize?client_id=${data.bot_id}&scope=bot&application.command&guild_id=${data.guild_id}`, "_blank")
                alert("invite-approve", "Almost there...", "Now invite bot to main server")
            }
        }
    }      
}

async function startSetup() {
    if(!wsUp) {
        info("Nightheart", "Waiting for ws to come up to start setup")
        wsStart()
        return
    }

    if(ws.readyState !== ws.OPEN) {
        if(wsFatal) {
            return
        }
        info("Nightheart", "WS is not open, restarting ws")
        wsUp = false
        startingWs = false
        wsStart()
        return
    }
}


readyModule("ws")