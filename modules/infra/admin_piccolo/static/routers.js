// This contains all of the routers for lynx

async function loadContent(loc) {
    if(wsFatal) {
        document.title = "Token Error"
        document.querySelector("#verify-screen").innerHTML = ""
        return
    }

    locSplit = loc.split("/")

    document.title = title(locSplit[locSplit.length - 1])

    clearInterval(myPermsInterval)

    inDocs = false

    loc = loc.replace('https://lynx.fateslist.xyz', '')

    currentLoc = loc.split("?")[0];

    if(loc.startsWith("/docs-src")) {
        // Create request for docs
        waitForWsAndLoad({loc: loc}, (data) => {
            info("Lionblaze", "Requested for docs-src")
            wsSend({request: "docs", path: data.loc.replace("/docs-src/", ""), source: true})
        })
        return
    } else if(loc.startsWith("/docs")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            info("Lionblaze", "Requested for docs")
            inDocs = true
            wsSend({request: "docs", path: data.loc.replace("/docs/", ""), source: false})
        })
        return
    } else if(loc.startsWith("/links")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            info("Lionblaze", "Requested for links")
            wsSend({request: "links"})
        })
        return
    } else if(loc.startsWith("/staff-guide")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            inDocs = true
            info("Lionblaze", "Requested for staff-guide (docs)")
            wsSend({request: "docs", "path": "staff-guide", source: false})
        })
        return
    } else if(loc.startsWith("/privacy")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            inDocs = true
            info("Lionblaze", "Requested for privacy (docs)")
            wsSend({request: "docs", "path": "privacy", source: false})
        })
        return
    } else if(loc.startsWith("/status")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            inDocs = true
            info("Lionblaze", "Requested for status (docs)")
            wsSend({request: "docs", "path": "status-page", source: false})
        })
        return
    } else if(loc.startsWith("/surveys")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            info("Lionblaze", "Requested for survey list")
            wsSend({request: "survey_list"})
        })
        return
    } else if(loc == "/" || loc == "") {
        waitForWsAndLoad({loc: loc}, (data) => {
            info("Lionblaze", "Requested for index")
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
            info("Lionblaze", "Requested for loa")
            wsSend({request: "loa"})
        })
        return
    } else if(loc.startsWith("/staff-apps")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            info("Lionblaze", "Requested for staff-apps list")
            const urlParams = new URLSearchParams(window.location.search);
            wsSend({request: "staff_apps", open: urlParams.get("open")})
        })
        return
    } else if(loc.startsWith("/user-actions")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            info("Lionblaze", "Requested for user-actions")
            const urlParams = new URLSearchParams(window.location.search);
            wsSend({request: "user_actions", data: {
                add_staff_id: urlParams.get("add_staff_id"),
            }})
        })
        return
    } else if(loc.startsWith("/requests")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            info("Lionblaze", "Requested for requests")
            wsSend({request: "request_logs"})
        })
        return 
    } else if(loc.startsWith("/reset")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            info("Lionblaze", "Requested for reset page")
            wsSend({request: "reset_page"})
        })
        return 
    } else if(loc.startsWith("/bot-actions")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            info("Lionblaze", "Requested for bot-actions")
            wsSend({request: "bot_actions"})
        })
        return
    } else if(loc.startsWith("/staff-verify")) {
        waitForWsAndLoad({loc: loc}, (data) => {
            info("Lionblaze", "Requested for staff-verify")
            wsSend({request: "staff_verify"})
        })
        return
    } else if(loc.startsWith("/admin")) {
        window.location.href = loc
    } else if(loc.startsWith("/apply")) { 
        waitForWsAndLoad({loc: loc}, (data) => {
            info("Lionblaze", "Requested for apply")
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

readyModule("routers")