// https://stackoverflow.com/a/46959528
function title(str) {
    return str.replaceAll("_", " ").replace(/(^|\s)\S/g, function(t) { return t.toUpperCase() });
}

if(!localStorage.ackedMsg) {
    localStorage.ackedMsg = JSON.stringify([])
}

var ackedMsg = JSON.parse(localStorage.ackedMsg);
async function getNotifications() {
    let resp = await fetch("https://lynx.fateslist.xyz/_notifications");
    if(resp.ok) {
        let data = await resp.json();
        data.forEach(function(notif) {
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
        $('#currentBreadPath').append(`<li class="breadcrumb-item active"><a href="${breadURL}">${currentBreadPath}</a></li>`)
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
        $('#docs-main-nav').toggleClass('menu-open')

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

async function isStaff() {
    let res = await fetch("/_perms", {
        method: "GET",
        credentials: 'same-origin',
        headers: {
            "Frostpaw-Staff-Notify": "0.1.0",
            "Accept": "application/json"
        },
    })

    let isStaff = 1;

    if(res.ok) {
        let body = await res.json()
        isStaff = body.perm
    }

    if(isStaff < 2) {
        console.log("User is not staff, hiding admin panel")

        // Remove admin panel
        $('#admin-panel-nav').remove()
        $('#lynx-admin-nav').remove()
        $('#staff-apps-nav').remove()
        $('.admin-only').remove()
    }

    return isStaff
}

docReady(async function() {
    setInterval(getNotifications, 5000)
    setTimeout(extraCode, 1000)

    // Fetch doctree (update v on doctree change if it doesnt update)
    let tree = await fetch("/_static/doctree.json?v=1")
    let treeData = await tree.json()

    $(treeData.doctree).insertBefore("#doctree")

    let res = await fetch(window.location.href + '?json=true', {
        method: "GET",
        credentials: 'same-origin',
        headers: {
            "Frostpaw-Staff-Notify": "0.1.0",
            "Accept": "application/json"
        },
    })

    isStaff = await isStaff()

    if(res.ok) {
        let body = await res.json()
        document.querySelector("#verify-screen").innerHTML = body.data
        document.querySelector("#title").innerHTML = body.title
        if(body.script) {
            let script = document.createElement("script")
            script.innerHTML = body.script
            document.body.appendChild(script)
        }

        if(body.ext_script) {
            let script = document.createElement("script")
            script.src = body.ext_script
            document.body.appendChild(script)
        }

        if(body.pre) {
            document.querySelector("#verify-screen").innerHTML += `<a href='${body.pre}'>Back to previous page</a>`
        }

        if(window.location.hash) {
            document.querySelector(`${window.location.hash}`).scrollIntoView()
        }
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

    // Check if admin and hide admin panel stuff if so
    if(isStaff < 2) {
        $('.admin-only').remove()
    }
})

