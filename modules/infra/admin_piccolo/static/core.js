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

var addedDocTree = false
var havePerm = false
var staffPerm = 1
var alreadyUp = false
var refresh = false

var hasLoadedAdminScript = false

var perms = {name: "Please wait for websocket to finish loading", perm: 0}

var user = {id: "0", username: "Please wait for websocket to finish loading"}

const wsContentResp = new Set(['docs', 'links', 'staff_guide', 'index', "request_logs", "reset_page", "staff_apps", "loa", "user_actions", "bot_actions", "staff_verify", "survey_list"])

function downloadTextFile(text, name) {
    const a = document.createElement('a');
    const type = name.split(".").pop();
    a.href = URL.createObjectURL( new Blob([text], { type:`text/${type === "txt" ? "plain" : type}` }) );
    a.download = name;
    a.click();
  }  

async function wsStart() {
    if(startingWs) {
        console.log("NOTE: Not starting WS when already starting or critically aborted")
        return
    }

    $("#ws-info").html("Starting websocket...")

    startingWs = true
    
    ws = new WebSocket("wss://lynx.fateslist.xyz/_ws")
    ws.onopen = function (event) {
        console.log("WS connection opened. Started promise to send initial auth")
        if(ws.readyState === ws.CONNECTING) {
            console.log("Still connecting not sending")
            return
        }

        wsUp = true
        if(!addedDocTree) {
            $("#ws-info").html("Fetching doctree from websocket")
            ws.send(JSON.stringify({request: "doctree"}))
        } 
        getNotifications() // Get initial notifications
    }

    ws.onclose = function (event) {
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

    ws.onmessage = function (event) {
        console.log(event.data);
        var data = JSON.parse(event.data)
        if(data.resp == "user_info") {
            $("#ws-info").html("Websocket auth success.")
            user = data.user
        } if(data.resp == "doctree") {
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
                    console.log(`${notif.id} is not pushed`)
                    notifCount = parseInt(document.querySelector("#notif-msg-count").innerText)
                    console.log(`Notification count is ${notifCount}`)
                    document.querySelector("#notif-msg-count").innerText = notifCount + 1
    
                    $(`<a href="#" class="dropdown-item"><i class="fas fa-envelope mr-2"></i><span class="float-right text-muted text-sm">${notif.message}</span></a>`).insertBefore("#messages")
    
                    pushedMessages.push(notif.id)
                }
    
                if(notif.acked_users.includes(data.user_id)) {
                    return;
                } else if(ackedMsg.includes(notif.id)) {
                    console.log(`Ignoring acked message: ${notif.id}`)
                    return;
                }
    
                if(notif.type == 'alert') {
                    alert(notif.message);
                    ackedMsg.push(notif.id)
                    localStorage.ackedMsg = JSON.stringify(ackedMsg);
                }
            })
        } else if(data.resp == "staff_verify_forced") {
            console.log("WS: Got request to enforce staff verify")
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
        } else if(data.resp == "user_action" || data.resp == "bot_action" || data.resp == "eternatus" || data.resp == "survey" || data.resp == "data_deletion") {
            alert(data.detail)
            if(data.resp == "bot_action" && data.guild_id) {
                // Now put the invite to the bot
                window.open(`https://discord.com/api/oauth2/authorize?client_id=${data.bot_id}&scope=bot&application.command&guild_id=${data.guild_id}`, "_blank")
                alert("Now invite bot to main server")
            }
        } else if(data.resp == "cosmog") {
            if(data.pass) {
                alert(data.detail)
                document.querySelector("#verify-screen").innerHTML = `<h4>Verified</h4><pre>Your lynx password is ${data.pass}</pre><br/><div id="verify-parent"><button id="verify-btn" onclick="window.location.href = '/'">Open Lynx</button></div>`
            } else {
                alert("Error: " + data.detail)
                document.querySelector("#verify-btn").innerText = "Verify";    
            }
        } else if(data.resp == "data_request") {
            console.log("WS: Got data request")
            if(data.detail) {
                alert(data.detail)
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
        alert(data.detail)
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
        script.src = data.ext_script
        document.body.appendChild(script)
    }

    if(data.pre) {
        document.querySelector("#verify-screen").innerHTML += `<a href='${data.pre}'>Back to previous page</a>`
    }

    if(window.location.hash) {
        document.querySelector(`${window.location.hash}`).scrollIntoView()
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
        ws.send(JSON.stringify({request: "notifs"}))
    } else {
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
    console.log({extraCode})
    $(".temp-item").remove()

    loadDocs()

    var currentURL = window.location.pathname
    console.log('Chnaging Breadcrumb Paths')

    var pathSplit = currentURL.split('/')

    var breadURL = ''

    pathSplit.forEach(el => {
        if(!el) {
            return
        }
        console.log(el)
        if(currentURL.startsWith("/docs/")) {
            breadURL += `#`
        } else {
            breadURL += `/${el}`
        }
        var currentBreadPath = title(el.replace('-', ' '))
        $('#currentBreadPath').append(`<li class="breadcrumb-item breadcrumb-temp active"><a href="${breadURL}">${currentBreadPath}</a></li>`)
    })

    currentURL = currentURL.replace('/', '') // Replace first

    currentURLID = '#' + currentURL.replaceAll('/', '-') + "-nav"
    if(currentURL == "") {
        currentURLID = "#home-nav"
    }

    if(currentURL == 'bot-actions') {
        document.querySelector("#admin-panel-nav").classList.add("menu-open")
    } else if(currentURL== 'user-actions') {
        document.querySelector("#admin-panel-nav").classList.add("menu-open")
    } 

    if(currentURLID.includes('docs')) {
        if(!alreadyUp) {
            $('#docs-main-nav').toggleClass('menu-open')
        }

        // Find the subnavs
        var tree = pathSplit[2]
        var navID = `#docs-${tree}-nav`
        $(navID).toggleClass('menu-open')
        console.log(navID)
    }

    try {
        document.querySelector(currentURLID).classList.add('active')
    } catch {
        console.log(`No active element found: ${currentURLID}`)
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
inStaffVerify = false

async function loadContent(loc) {
    if(loc.startsWith("/staff-verify") && inStaffVerify) {
        console.log("Ignoring fake alarm for force staff verify")
        return
    }

    locSplit = loc.split("/")

    document.title = title(locSplit[locSplit.length - 1])

    inStaffVerify = false

    clearInterval(myPermsInterval)

    loc = loc.replace('https://lynx.fateslist.xyz', '')

    if(loc.includes("/docs-src")) {
        // Create request for docs
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for docs")
            ws.send(JSON.stringify({request: "docs", path: data.loc.replace("/docs-src/", ""), source: true}))
        })
        return
    } else if(loc.includes("/docs")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for docs-src")
            ws.send(JSON.stringify({request: "docs", path: data.loc.replace("/docs/", ""), source: false}))
        })
        return
    } else if(loc.startsWith("/links")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for links")
            ws.send(JSON.stringify({request: "links"}))
        })
        return
    } else if(loc.startsWith("/staff-guide")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            ws.send(JSON.stringify({request: "docs", "path": "staff-guide", source: false}))
            return
        })
    } else if(loc.startsWith("/privacy")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            ws.send(JSON.stringify({request: "docs", "path": "privacy", source: false}))
            return
        })
    } else if(loc.startsWith("/status")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            ws.send(JSON.stringify({request: "docs", "path": "status-page", source: false}))
            return
        })
    } else if(loc.startsWith("/surveys")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for survey list")
            ws.send(JSON.stringify({request: "survey_list"}))
        })
        return
    } else if(loc == "/" || loc == "") {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for index")
            ws.send(JSON.stringify({request: "index"}))
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
            ws.send(JSON.stringify({request: "loa"}))
        })
        return
    } else if(loc.startsWith("/staff-apps")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for staff-apps")
            const urlParams = new URLSearchParams(window.location.search);
            ws.send(JSON.stringify({request: "staff_apps", open: urlParams.get("open")}))
        })
        return
    } else if(loc.startsWith("/user-actions")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for user-actions")
            const urlParams = new URLSearchParams(window.location.search);
            ws.send(JSON.stringify({request: "user_actions", data: {
                add_staff_id: urlParams.get("add_staff_id"),
            }}))
        })
        return
    } else if(loc.startsWith("/requests")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for requests")
            ws.send(JSON.stringify({request: "request_logs"}))
        })
        return 
    } else if(loc.startsWith("/reset")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for reset_page")
            ws.send(JSON.stringify({request: "reset_page"}))
        })
        return 
    } else if(loc.startsWith("/bot-actions")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for bot-actions")
            ws.send(JSON.stringify({request: "bot_actions"}))
        })
        return
    } else if(loc.startsWith("/staff-verify")) {
        inStaffVerify = true
        waitForWsAndLoad({loc: loc}, (data) => {
            console.log("WS: Requested for staff-verify")
            ws.send(JSON.stringify({request: "staff_verify"}))
        })
        return
    } else if(loc.startsWith("/admin")) {
        window.location.href = loc
    } else {
        document.querySelector("#verify-screen").innerHTML = "Animus magic is broken today!"
        document.querySelectorAll(".content")[0].innerHTML = `<h4>404<h4><a href='/'>Index</a><br/><a href='/links'>Some Useful Links</a></h4>`
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
                    $(".breadcrumb-temp").remove()
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
    $(".breadcrumb-temp").remove()
    loadContent(window.location.pathname)
}

document.body.addEventListener('click', function(event) {
    // main-sidebar
    if(event.target.id == "sidebar-overlay") {
        $('#toggle-sidebar').PushMenu('toggle');
    }
}, true); 
