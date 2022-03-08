// https://stackoverflow.com/a/46959528
function title(str) {
    return str.replaceAll("_", " ").replace(/(^|\s)\S/g, function(t) { return t.toUpperCase() });
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

var perms = {name: "Please wait for websocket to finish loading", perm: 0}

var user = {username: "Please wait for websocket to finish loading"}

async function authWs() {
    // Fetch base user information from server
    let res = await fetch("/_user", {
        method: "GET",
        credentials: 'same-origin',
        headers: {
            "Frostpaw-Staff-Notify": "0.1.0",
            "Frostpaw-Websocket-Conn": "connecting",
            "Accept": "application/json"
        },
    })

    wsData = {}

    if(!res.ok) {
        if(res.status == 502) {
            console.log("Failed to connect to server during ws auth connection")
            return
        }
        console.log("Using no-auth ws due to failed call to /_user")
    } else {
        try {
            wsData = await res.json()
        } catch {
            console.log("Request was 200 yet was not valid JSON. Aborting WS. Likely user token mismatch")
            return
        }
    }    

    user = wsData

    ws.send(JSON.stringify({request: "upgrade", data: wsData}))
}

async function wsStart() {
    if(startingWs) {
        console.log("NOTE: Not starting WS when already starting or critically aborted")
        return
    }

    document.querySelector("#verify-screen").innerHTML = `<div id="loader"><strong>WS is starting. Certain actions may be unavailable</strong></div>${document.querySelector("#verify-screen").innerHTML}`

    startingWs = true
    
    ws = new WebSocket("wss://lynx.fateslist.xyz/_ws")
    ws.onopen = function (event) {
        console.log("WS connection opened. Started promise to send initial auth")
        if(ws.readyState === ws.CONNECTING) {
            console.log("Still connecting not sending")
            return
        }

        authWs()

        $("#loader").html("<strong>Now sending auth to websocket</strong>")

        wsUp = true
        if(!addedDocTree) {
            $("#loader").html("Fetching doctree from websocket")
            ws.send(JSON.stringify({request: "doctree"}))
        } 
        getNotifications() // Get initial notifications
    }

    ws.onclose = function (event) {
        console.log(event, "WS: Closed due to an error")
        wsUp = false
        startingWs = false
        return
    }

    ws.onerror = function (event) {
        console.log(event, "WS: Closed due to an error")
        wsUp = false
        startingWs = false
        return
    }

    ws.onmessage = function (event) {
        console.log(event.data);
        var data = JSON.parse(event.data)
        if(data.resp == "doctree") {
            console.log("WS: Got doctree")
            addedDocTree = true
            $(data.data).insertBefore("#doctree")
            extraCode()
        } else if(data.resp == "notifs") {
            console.log("WS: Got notifications")
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
        } else if(data.resp == "perms") {
            if(!havePerm) {
                $("#loader").remove()
            }

            havePerm = true
            console.log("WS: Got permissions")
            perms = data.data
            staffPerm = data.data.perm

            // Remove admin panel
            if(staffPerm < 2) {
                delNotAdmin()
                setInterval(delNotAdmin, 500)
            }
        } else if(data.resp == "reset") {
            console.log("WS: Credentials reset")
            
            // Kill websocket
            ws.close(4999, "Credentials reset")
            document.querySelector("#verify-screen").innerHTML = "Credential reset successful!"
        } else if(data.resp == "docs") {
            console.log("WS: Got docs")   
            setData(data)
        } else if(data.resp == "links") {
            console.log("WS: Got links")   
            setData(data)
        } else if(data.resp == "staff_guide") {
            console.log("WS: Got staff guide")   
            setData(data)
        } else if(data.resp == "index") {
            console.log("WS: Got index")   
            setData(data)
        }
        else if(data.resp == "loa") {
            console.log("WS: Got loa")   
            setData(data, () => {
                ws.send(JSON.stringify({request: "loa"}))
            })
        }
    }      
}

async function upgradeAndSend(f) {
    await authWs()
    f()
}

function setData(data, noExtraCode=false, upgFunc=null) {
    if(data.wait_for_upg) {
        console.log("WS: Waiting for upgrade")
        upgradeAndSend(upgFunc)
        return
    }

    if(data.detail) {
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
        linkMod()
    } else if(noExtraCode && !contentLoadedOnce) {
        linkMod()
    }

    contentLoadedOnce = true
    contentCurrPage = window.location.pathname
}

function delNotAdmin() {
    $('#admin-panel-nav').remove()
    $('#lynx-admin-nav').remove()
    $('#staff-apps-nav').remove()
    $('.admin-only').remove()
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
    $(".temp-item").remove()

    var currentURL = window.location.pathname
    console.log('Chnaging Breadcrumb Paths')

    var pathSplit = currentURL.split('/')

    var breadURL = ''

    pathSplit.forEach(el => {
        if(!el) {
            return
        }
        console.log(el)
        breadURL += `/${el}`
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
        if(contentCurrPage == data.loc && contentLoadedOnce) {
            console.log("Ignoring bad request", contentCurrPage, data.loc)
            return
        }

        f(data)
        return
    }
}

myPermsInterval = -1

async function loadContent(loc) {
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
            console.log("WS: Requested for staff-guide")
            ws.send(JSON.stringify({request: "staff_guide"}))
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
    }

    console.log(loc)

    if(loc.startsWith("/admin")) {
        window.location.href = res.url
    }

    let res = await fetch(loc + '?json=true', {
        method: "GET",
        credentials: 'same-origin',
        headers: {
            "Frostpaw-Staff-Notify": "0.1.0",
            "Accept": "application/json"
        },
    })

    if(res.url.startsWith("https://fateslist.xyz/frostpaw/herb")) {
        window.location.href = res.url
    }

    if(res.ok) {
        let body = await res.json()
        setData(body)
    } else {
        let status = res.status

        if(status == 404) {
            status = `<h1>404</h1><h3>Page not found</h3>`
        } else {
            status = `<h1>${status}</h1>`
        }

        document.querySelector("#title-full").innerHTML = "Animus magic is broken today!"
        document.querySelectorAll(".content")[0].innerHTML = `${status}<h4><a href='/'>Index</a><br/><a href='/links'>Some Useful Links</a></h4>`
    }

    linkMod()
}

async function linkMod() {
    links = document.querySelectorAll("a")
    links.forEach(link => {
        console.log(link, link.href, link.hasPatched, link.hasPatched == undefined)
        if(link.href.startsWith("https://lynx.fateslist.xyz/") && link.hasPatched == undefined) {
            if(link.href == "https://lynx.fateslist.xyz/#") {
                return // Don't patch # elements
            } 
            if(link.href == window.location.href || link.href.endsWith("#")) {
                return // Don't patch if same url
            }

            link.hasPatched = true
            console.log("Add patch")
            link.addEventListener('click', event => {
                if ( event.preventDefault ) event.preventDefault();
                // Now add some special code
                window.history.pushState(window.location.pathname, 'Loading...', link.href);
                handler = async () => {
                    $(".active").toggleClass("active")
                    $(".breadcrumb-temp").remove()
                    await loadContent(link.href)
                    await extraCode()
                }

                handler()
            })
        }
    })
}