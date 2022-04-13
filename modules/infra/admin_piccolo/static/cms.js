// Content Management System for Lynx

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
        loadModule(data.ext_script, assetList[data.ext_script])
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

async function extraCode() {
    debug("Larksong", "Running extra code")
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
        debug("Larksong", "Got docs nav id", { navID })
    }

    try {
        document.querySelector(currentURLID).classList.add('active')
    } catch {
        warn("Larksong", `No active element found: ${currentURLID}`)
    }
}

function clearRefresh() {
    document.querySelector(".refresh-btn").classList.remove("refresh-btn-active")
    document.querySelector(".refresh-btn").classList.remove("disabled")
}

function loginUser() {
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

function waitForWsAndLoad(data, f) {
    if(!wsUp) {
        // Websocket isn't up yet
        waitInterval = setInterval(function() {
            if(wsUp) {
                info("Larksong", "WS is up, loading content")
                loadContent(data.loc)
                clearInterval(waitInterval)
            }
        }, 500)
        return
    } else {
        // Websocket is up, load content
        info("Larksong", "WS is up, loading content")
        try {
            clearInterval(waitInterval)
        } catch(err) {
            err("Larksong", err)
        }
        info("Larksong", "Requested for data")

        // Are we even in a new page
        if(contentCurrPage == data.loc && contentLoadedOnce && !refresh) {
            info("Larksong", "Ignoring bad request as not in new page", contentCurrPage, data.loc)
            return
        }

        f(data)
        return
    }
}

async function linkMod() {
    links = document.querySelectorAll("a")
    links.forEach(link => {
        console.debug("[Sparkpelt]", link, link.href, link.hasPatched, link.hasPatched == undefined)
        if(link.href.startsWith("https://lynx.fateslist.xyz/") && link.hasPatched == undefined) {
            if(link.href == "https://lynx.fateslist.xyz/#") {
                return // Don't patch # elements
            } 
            if(link.href == window.location.href || link.href.endsWith("#") || link.pathname == window.location.pathname) {
                return // Don't patch if same url
            }

            link.hasPatched = true
            console.debug("[Sparkpelt] Add patch")
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

$(function() {
    if(!alreadyUp) {
        interval = setInterval(function() {
            if(modulesLoaded.includes("ws") && modulesLoaded.includes("cstate") && modulesLoaded.includes("cms") && modulesLoaded.includes("routers") && modulesLoaded.includes("alert")) {
                clearInterval(interval)
                startSetup()
                setInterval(startSetup, 5000)    
                loadContent(window.location.pathname)
                alreadyUp = true 
                clearInterval(interval)     
            }
        })
    }
})

readyModule("cms")