var interval = -1
var sentExit = false

function modConsole() {
    // Modify console before it's used
    if(!window.frames[0]) {
        return
    }

    window.frames[0].console.log = function(...args) {
        info("Poppypaw", ...args)
    }

    window.frames[0].console.info = function(...args) {
        info("Poppypaw", ...args)
    }

    window.frames[0].console.debug = function(...args) {
        debug("Poppypaw", ...args)
    }

    try {
        // Force enable dark mode
        window.frames[0].document.querySelector("#app").classList = "dark_mode"
    } catch {}

    window.frames[0].window.location.hash = window.location.hash
}

function loadAdminConsole() {
    // Inject primitives
    adminPatchCalled = false
    sentExit = false
    window.log = log
    window.info = info
    window.debug = debug
    window.warn = warn
    window.error = error

    iframe = document.querySelector('#admin-iframe')
    info("Poppypaw", "Admin iframe found", { iframe })

    // Modify console before it's used
    modInterval = setInterval(modConsole)

    iframe.src = iframe.getAttribute("data-src") + window.location.hash

    iframe.onload = () => {
        xhrObj = window.frames[0].XMLHttpRequest;
        xhrObj.origOpen = xhrObj.prototype.open;
        window.frames[0].XMLHttpRequest.prototype.open = function () {
            info("Poppypaw", "XMLHttpRequest.open", ...arguments)
            xhrObj.origOpen.apply(this, arguments);
            this.setRequestHeader('X-Lynx-Site', 'true');
        };

        let script = iframe.contentWindow.document.createElement("script")
        script.src = assetList["admin-console"]
        iframe.contentWindow.document.body.appendChild(script)

        setTimeout(() => {
            clearInterval(modInterval)
        }, 1000)
    };

    iframe.setAttribute("data-loaded", "true")

    interval = setInterval(() => {
        if(!currentLoc.startsWith("/admin")) {
            if(!sentExit) {
                info("Poppypaw", "Exiting admin iframe")
                sentExit = true
            }
            clearInterval(interval)
            return
        } else {
            iframe = document.querySelector('#admin-iframe')
            if(iframe.getAttribute("data-loaded") !== "true") {
                loadAdminConsole()
            }

            let ifSrc = iframe.contentWindow.location.href.replace("_admin", "admin")

            if(ifSrc !== window.location.href && ifSrc.startsWith("https://")) {
                info("Poppypaw", "Admin iframe src changed", { ifSrc })
                window.history.pushState(ifSrc, 'New page...', ifSrc);
            }
        }
    })
}

$(loadAdminConsole)

readyModule("admin-iframe")