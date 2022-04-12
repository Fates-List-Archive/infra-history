// https://stackoverflow.com/a/46959528
function title(str) {
    return str.replaceAll("-", " ").replaceAll("_", " ").replace(/(^|\s)\S/g, function(t) { return t.toUpperCase() });
}

if(!localStorage.ackedMsg) {
    localStorage.ackedMsg = JSON.stringify([])
}

var ackedMsg = JSON.parse(localStorage.ackedMsg);
var pushedMessages = [];

var wsUp = false
var ws = null
var startingWs = false;
var wsFatal = false
var forcedStaffVerify = false

var inDocs = false

var addedDocTree = false
var havePerm = false
var staffPerm = 1
var alreadyUp = false
var refresh = false

var currentLoc = window.location.pathname

var hasLoadedAdminScript = false

var perms = {name: "Please wait for websocket to finish loading", perm: 0}

var user = {id: "0", username: "Please wait for websocket to finish loading"}

const wsContentResp = new Set(['docs', 'links', 'staff_guide', 'index', "request_logs", "reset_page", "staff_apps", "loa", "user_actions", "bot_actions", "staff_verify", "survey_list", "get_sa_questions"])

const wsContentSpecial = new Set(['user_action', 'bot_action', 'eternatus', 'survey', 'data_deletion', 'apply_staff', 'send_loa'])

var assetList = {};

function getNonce() {
	// Protect against simple regexes with this
	return ("C" + "a") + "t" + "m".repeat(1) + "i".repeat(1) + "n" + "t".repeat(1) + "s".repeat(0)
}

function downloadTextFile(text, name) {
    const a = document.createElement('a');
    const type = name.split(".").pop();
    a.href = URL.createObjectURL( new Blob([text], { type:`text/${type === "txt" ? "plain" : type}` }) );
    a.download = name;
    a.click();
}  

async function wsSend(data) {
    if(!wsUp) {
        console.log("Waiting for ws to come up to start recieveing notification")
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
    console.log("WS is not open, restarting ws")
    wsUp = false
    startingWs = false
    wsStart()
    return
}

async function wsStart() {
    // Starts a websocket connection
    if(startingWs) {
        console.log("NOTE: Not starting WS when already starting or critically aborted")
        return
    }

    $("#ws-info").html("Starting websocket...")

    startingWs = true

    // Select the client
    let cliExt = Date.now()
    
    ws = new WebSocket(`wss://lynx.fateslist.xyz/_ws?cli=${getNonce()}@${cliExt}&plat=WEB`)
    ws.onopen = function (event) {
        console.log("WS connection opened. Started promise to send initial auth")
        if(ws.readyState === ws.CONNECTING) {
            console.log("Still connecting not sending")
            return
        }

        wsUp = true
        if(!addedDocTree) {
            $("#ws-info").html("Fetching doctree from websocket")
            wsSend({request: "doctree"})
        } 
        getNotifications() // Get initial notifications
    }

    ws.onclose = function (event) {
        if(event.code == 4008) {
            // Token error
            console.log("Token/Client error, requesting a login")
            wsUp = true;
            startingWs = true;
            wsFatal = true;
            $("#ws-info").html("Invalid token/client, login again using Login button in sidebar or refreshing your page")
            return
        }

        $("#ws-info").html("Websocket unexpectedly closed, likely server maintenance")
        console.log(event, "WS: Closed due to an error")
        wsUp = false
        startingWs = false
        return
    }

    ws.onerror = function (event) {
        $("#ws-info").html("Websocket unexpectedly errored, likely server maintenance")
        console.log(event, "WS: Closed due to an error")
        wsUp = false
        startingWs = false
        return
    }

    ws.onmessage = async function (event) {
        var data = await MessagePack.decodeAsync(event.data.stream())
        console.log(data)
        if(data.resp == "user_info") {
            $("#ws-info").html("Websocket auth success.")
            user = data.user
        } else if(data.resp == "asset-list") {
            console.log("Got static asset list")
            assetList = data.assets
        } else if(data.resp == "spld") {
            console.log(`Got a spld (server pipeline) message: ${data.e}`)
            if(data.e == "M") {
                console.log("Server is in maintenance mode. Alerting user to this")
                alert("maint", "Maintenance", "Lynx is now down for maintenance, certain actions may be unavailable during this time!")
            } else if(data.e == "RN") {
                console.log("Server says refresh is needed")
                if(!data.loc || data.loc == currentLoc) {
                    refreshPage()
                } else {
                    console.log("Refresh does not pertain to us!")
                }
            } else if(data.e == "MP") {
                console.log("Server says we do not have the required permissions")
                loadContent(`/missing-perms?min-perm=${data.min_perm || 2}`)
            } else if(data.e == "OD") {
		console.log("Client out of date. Invalid nonce?")
		alert("nonce-err", "Hmmm...", "Your Lynx client is a bit out of date. Consider refreshing your page?")
	    }
        } else if(data.resp == "doctree") {
            console.log("WS: Got doctree")
            addedDocTree = true
            $(data.data).insertBefore("#doctree")
        } else if(data.resp == "notifs") {
            console.log("WS: Got notifications")
            $("#ws-info").text(`Websocket still connected as of ${Date()}`)
            data.data.forEach(function(notif) {
                // Before ignoring acked message, check if its pushed
                if(!pushedMessages.includes(notif.id)) {
                    // Push the message
                    console.debug(`${notif.id} is not pushed`)
                    notifCount = parseInt(document.querySelector("#notif-msg-count").innerText)
                    console.debug(`Notification count is ${notifCount}`)
                    document.querySelector("#notif-msg-count").innerText = notifCount + 1
    
                    $(`<a href="#" class="dropdown-item"><i class="fas fa-envelope mr-2"></i><span class="float-right text-muted text-sm">${notif.message}</span></a>`).insertBefore("#messages")
    
                    pushedMessages.push(notif.id)
                }
    
                if(notif.acked_users.includes(data.user_id)) {
                    return;
                } else if(ackedMsg.includes(notif.id)) {
                    console.debug(`Ignoring acked message: ${notif.id}`)
                    return;
                }
    
                if(notif.type == 'alert') {
                    alert(`notif-urgent`, "Urgent Notification", notif.message);
                    ackedMsg.push(notif.id)
                    localStorage.ackedMsg = JSON.stringify(ackedMsg);
                }
            })
        } else if(data.resp == "staff_verify_forced") {
            if(inDocs) {
                return
            }
            console.log("WS: Got request to enforce staff verify")
            forcedStaffVerify = true
            loadContent("/staff-verify")
            return
        } else if(data.resp == "perms") {
            $("#ws-info").html(`Websocket perm update done to ${data.data}`)
            havePerm = true
            console.log("WS: Got permissions")
            perms = data.data
            staffPerm = data.data.perm

            // Remove admin panel
            if(staffPerm >= 2) {
                if(!hasLoadedAdminScript) {
                    let script = document.createElement("script")
                    script.src = "/_static/admin-nav.js?v=132492"
                    document.body.appendChild(script)
                    hasLoadedAdminScript = true
                } else {
                    loadAdmin()
                }
                $('.admin-only').css("display", "block")
            }
            setInterval(() => {
                if(staffPerm < 2) {
                    $(".admin-only").css("display", "none")
                }
            })
        } else if(data.resp == "reset") {
            $("#ws-info").html(`Websocket cred-reset called`)
            console.log("WS: Credentials reset")
            
            // Kill websocket
            ws.close(4999, "Credentials reset")
            document.querySelector("#verify-screen").innerHTML = "Credential reset successful!"
        } else if(wsContentResp.has(data.resp)) {
            console.log(`WS: Got ${data.resp}`)   
            setData(data)
        } else if(wsContentSpecial.has(data.resp)) {
            alert("special-status-upd", "Status Update!", data.detail)
            if(data.resp == "bot_action" && data.guild_id) {
                // Now put the invite to the bot
                window.open(`https://discord.com/api/oauth2/authorize?client_id=${data.bot_id}&scope=bot&application.command&guild_id=${data.guild_id}`, "_blank")
                alert("invite-approve", "Almost there...", "Now invite bot to main server")
            }
        } else if(data.resp == "cosmog") {
            if(data.pass) {
                alert("success-verify", "Success!", data.detail)
                document.querySelector("#verify-screen").innerHTML = `<h4>Verified</h4><pre>Your lynx password is ${data.pass}</pre><br/><div id="verify-parent"><button id="verify-btn" onclick="window.location.href = '/'">Open Lynx</button></div>`
            } else {
                alert("fail-verify", "Verification Error!", data.detail)
                document.querySelector("#verify-btn").innerText = "Verify";    
            }
        } else if(data.resp == "data_request") {
            console.log("WS: Got data request")
            if(data.detail) {
                alert("data-del", "Data deletion error", data.detail)
                document.querySelector("#request-btn").innerText = "Request"
                return
            } else if(data.data) {
                downloadTextFile(JSON.stringify(data.data), `data-request-${data.user}.json`)
                hljs.highlightAll();
                window.highlightJsBadge();
                document.querySelector("#request-btn").innerText = "Requested"
                document.querySelector("#request-btn").ariaDisabled = true
                document.querySelector("#request-btn").setAttribute("disabled", "true")
            }
        } 
    }      
}

function clearRefresh() {
    document.querySelector(".refresh-btn").classList.remove("refresh-btn-active")
    document.querySelector(".refresh-btn").classList.remove("disabled")
}

function setData(data, noExtraCode=false) {
    refresh = false
    if(data.detail) {
        clearRefresh()
        alert("note-ws", "Important Note", data.detail)
        return
    }
    document.querySelector("#verify-screen").innerHTML = data.data
    document.querySelector("#title").innerHTML = data.title    

    if(data.script) {
        let script = document.createElement("script")
        script.innerHTML = data.script
        document.body.appendChild(script)
    }

    if(data.ext_script) {
        let script = document.createElement("script")
        script.src = assetList[data.ext_script]
        document.body.appendChild(script)
    }

    if(data.pre) {
        document.querySelector("#verify-screen").innerHTML += `<a href='${data.pre}'>Back to previous page</a>`
    }

    if(window.location.hash) {
	setTimeout(() => document.querySelector(`${window.location.hash}`).scrollIntoView(), 300)
    }    

    if(!noExtraCode) {
        extraCode()
        linkMod()
    } else if(noExtraCode && !contentLoadedOnce) {
        linkMod()
    }

    contentLoadedOnce = true
    contentCurrPage = window.location.pathname

    $('#sidebar-search').SidebarSearch('init')

    clearRefresh()
}

async function getNotifications() {
    if(!wsUp) {
        console.log("Waiting for ws to come up to start recieveing notification")
        wsStart()
        return
    }

    if(ws.readyState === ws.OPEN) {
        wsSend({request: "notifs"})
    } else {
        if(wsFatal) {
            return
        }
        console.log("WS is not open, restarting ws")
        wsUp = false
        startingWs = false
        wsStart()
        return
    }
}

function docReady(fn) {
    // see if DOM is already available
    if (document.readyState === "complete" || document.readyState === "interactive") {
        // call on next available tick
        setTimeout(fn, 1);
    } else {
        document.addEventListener("DOMContentLoaded", fn);
    }
}    

async function extraCode() {
    console.debug({extraCode})
    $(".temp-item").remove()

    loadDocs()

    var currentURL = window.location.pathname

    var pathSplit = currentURL.split('/')

    currentURL = currentURL.replace('/', '') // Replace first

    var currentURLID = '#' + currentURL.replaceAll('/', '-') + "-nav"
    if(currentURL == "") {
        currentURLID = "#home-nav"
    }

    if(currentURL == 'bot-actions') {
        document.querySelector("#admin-panel-nav").classList.add("menu-open")
    } else if(currentURL == 'user-actions') {
        document.querySelector("#admin-panel-nav").classList.add("menu-open")
    } 

    if(currentURLID.includes('docs')) {
        $('#docs-main-nav').addClass('menu-open')

        // Find the subnavs
        var tree = pathSplit[2]
        var navID = `#docs-${tree}-nav`
        $(navID).addClass('menu-open')
        console.debug(navID)
    }

    try {
        document.querySelector(currentURLID).classList.add('active')
    } catch {
        console.debug(`No active element found: ${currentURLID}`)
    }
}

contentLoadedOnce = false
contentCurrPage = window.location.pathname

docReady(function() {
    if(!alreadyUp) {
        getNotifications()
        setInterval(getNotifications, 5000)
        loadContent(window.location.pathname)
        alreadyUp = true
    }
})

waitInterval = -1

function waitForWsAndLoad(data, f) {
    if(!wsUp) {
        // Websocket isn't up yet
        waitInterval = setInterval(function() {
            if(wsUp) {
                console.log("WS is up, loading content")
                loadContent(data.loc)
                clearInterval(waitInterval)
            }
        }, 500)
        return
    } else {
        // Websocket is up, load content
        console.log("WS is up, loading content")
        try {
            clearInterval(waitInterval)
        } catch(err) {
            console.log(err)
        }
        console.log("WS: Requested for data")

        // Are we even in a new page
        if(contentCurrPage == data.loc && contentLoadedOnce && !refresh) {
            console.log("Ignoring bad request", contentCurrPage, data.loc)
            return
        }

        f(data)
        return
    }
}

myPermsInterval = -1
inStaffVerify = 0

async function loadContent(loc) {
    if(wsFatal) {
        document.title = "Token Error"
        document.querySelector("#verify-screen").innerHTML = ""
        return
    } else if(forcedStaffVerify && inStaffVerify < 1) {
        clearRefresh()
        return
    }

    inStaffVerify++

    if(loc.startsWith("/staff-verify") && inStaffVerify > 3) {
        console.log("Ignoring fake alarm for force staff verify")
        clearRefresh()
        return
    }

    locSplit = loc.split("/")

    document.title = title(locSplit[locSplit.length - 1])

    clearInterval(myPermsInterval)

    inDocs = false

    loc = loc.replace('https://lynx.fateslist.xyz', '')

    currentLoc = loc;

    if(loc.startsWith("/docs-src")) {
        // Create request for docs
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for docs-src")
            wsSend({request: "docs", path: data.loc.replace("/docs-src/", ""), source: true})
        })
        return
    } else if(loc.startsWith("/docs")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for docs")
            inDocs = true
            wsSend({request: "docs", path: data.loc.replace("/docs/", ""), source: false})
        })
        return
    } else if(loc.startsWith("/links")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for links")
            wsSend({request: "links"})
        })
        return
    } else if(loc.startsWith("/staff-guide")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            inDocs = true
            wsSend({request: "docs", "path": "staff-guide", source: false})
        })
        return
    } else if(loc.startsWith("/privacy")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            inDocs = true
            wsSend({request: "docs", "path": "privacy", source: false})
        })
        return
    } else if(loc.startsWith("/status")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            inDocs = true
            wsSend({request: "docs", "path": "status-page", source: false})
        })
        return
    } else if(loc.startsWith("/surveys")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for survey list")
            wsSend({request: "survey_list"})
        })
        return
    } else if(loc == "/" || loc == "") {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for index")
            wsSend({request: "index"})
        })
        return
    } else if(loc.startsWith("/my-perms")) {
        myPermsInterval = setInterval(() => {
            if(user.token) {
                user.username = user.user.username
                user.id = user.user.id
            }

            setData({
                title: "My Perms",
                data: `
    Permission Name: ${perms.name}<br/>
    Permission Number: ${perms.perm}<br/>
    Is Staff: ${perms.perm >= 2}<br/>
    Is Admin: ${perms.perm >= 4}<br/>
    Permission JSON: ${JSON.stringify(perms)}

    <h4>User</h4>
    Username: ${user.username}<br/>
    User ID: ${user.id}
                `
            }, true)
            return
        }, 500)
        return
    } else if(loc.startsWith("/loa")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for loa")
            wsSend({request: "loa"})
        })
        return
    } else if(loc.startsWith("/staff-apps")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for staff-apps")
            const urlParams = new URLSearchParams(window.location.search);
            wsSend({request: "staff_apps", open: urlParams.get("open")})
        })
        return
    } else if(loc.startsWith("/user-actions")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for user-actions")
            const urlParams = new URLSearchParams(window.location.search);
            wsSend({request: "user_actions", data: {
                add_staff_id: urlParams.get("add_staff_id"),
            }})
        })
        return
    } else if(loc.startsWith("/requests")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for requests")
            wsSend({request: "request_logs"})
        })
        return 
    } else if(loc.startsWith("/reset")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for reset_page")
            wsSend({request: "reset_page"})
        })
        return 
    } else if(loc.startsWith("/bot-actions")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for bot-actions")
            wsSend({request: "bot_actions"})
        })
        return
    } else if(loc.startsWith("/staff-verify")) {
        inStaffVerify += 1
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for staff-verify")
            wsSend({request: "staff_verify"})
        })
        return
    } else if(loc.startsWith("/admin")) {
        window.location.href = loc
    } else if(loc.startsWith("/apply")) { 
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for apply")
            wsSend({request: "get_sa_questions"})
        })
        return
    } else if(loc.startsWith("/missing-perms")) {
        alert("missing-perms", "Missing Permissions", "You do not have permission to view this page.")
        setData({"title": "401 - Unauthorized", "data": `Unauthorized User`})
    } else {
        document.querySelector("#verify-screen").innerHTML = "Animus magic is broken today!"
        setData({"title": "404 - Not Found", "data": `<h4>404<h4><a href='/'>Index</a><br/><a href='/links'>Some Useful Links</a></h4>`})
    }

    linkMod()
}

async function linkMod() {
    links = document.querySelectorAll("a")
    links.forEach(link => {
        console.debug(link, link.href, link.hasPatched, link.hasPatched == undefined)
        if(link.href.startsWith("https://lynx.fateslist.xyz/") && link.hasPatched == undefined) {
            if(link.href == "https://lynx.fateslist.xyz/#") {
                return // Don't patch # elements
            } 
            if(link.href == window.location.href || link.href.endsWith("#") || link.pathname == window.location.pathname) {
                return // Don't patch if same url
            }

            link.hasPatched = true
            console.debug("Add patch")
            link.addEventListener('click', event => {
                if ( event.preventDefault ) event.preventDefault();
                // Now add some special code
                window.history.pushState(window.location.pathname, 'Loading...', link.href);
                handler = async () => {
                    $(".active").toggleClass("active")
                    await loadContent(link.href)
                }

                handler()
            })
        }
    })
}

function loginUser() {
    /* if(user.id == "0" || !user.id) {
        window.location.href = `https://fateslist.xyz/frostpaw/herb?redirect=${window.location.href}`
    } else {
        // TODO: Logout functionality in sunbeam
        window.location.href = `https://fateslist.xyz/frostpaw/deathberry?redirect=${window.location.href}`
    } */
    window.location.href = `https://fateslist.xyz/frostpaw/herb?redirect=${window.location.href}`
}

function refreshPage() {
    document.querySelector(".refresh-btn").classList.add("refresh-btn-active")
    document.querySelector(".refresh-btn").classList.add("disabled")
    refresh = true
    $(".active").toggleClass("active")
    loadContent(window.location.pathname)
}

document.body.addEventListener('click', function(event) {
    // main-sidebar
    if(event.target.id == "sidebar-overlay") {
        $('#toggle-sidebar').PushMenu('toggle');
    }
}, true); 
