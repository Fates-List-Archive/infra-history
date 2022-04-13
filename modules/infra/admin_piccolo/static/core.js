function docReady(fn) {
    // see if DOM is already available
    if (document.readyState === "complete" || document.readyState === "interactive") {
        // call on next available tick
        setTimeout(fn, 1);
    } else {
        document.addEventListener("DOMContentLoaded", fn);
    }
}    

// Custom logger
const log = (...args) => {
    const logLevels = ["debug", "info", "warn", "error"];

    logLevel = args[0].toLowerCase()

    if(!logLevels.includes(logLevel)) {
        args.unshift("info")
        return log(...args)
    }

    f = null

    // Get the loglevel
    f = console[logLevel]

    f(`%c[${args[1]}]%c`, "color: purple; font-weight: bold;", "", ...args.slice(2))
}

const debug = (...args) => {
    args.unshift("debug")
    return log(...args)
}
const info = (...args) => {
    args.unshift("info")
    return log(...args)
}
const warn = (...args) => {
    args.unshift("warn")
    return log(...args)
}
const error = (...args) => {
    args.unshift("error")
    return log(...args)
}

// Module loader
modulesLoaded = []

function readyModule(name) {
    info("StarClan", `Module: ${name} has loaded successfully!`)
    modulesLoaded.push(name)
}

function loadModule(name, path, callback = () => {}) {
    info("StarClan", `Loading module ${name} (path=${path})`)
    let script = document.createElement("script")
    script.src = path
    script.async = false
    document.body.appendChild(script)

    setInterval(function(){
        if(modulesLoaded.includes(name)) {
            callback()
            clearInterval(this)
        }
    })
}

// Load core modules
loadModule("doctree", "/_static/doctree.js?v=2")
loadModule("docs", "/_static/docs.js?v=m1")
loadModule("utils", "/_static/utils.js?v=m1")
loadModule("ws", "/_static/ws.js?v=m5")
loadModule("cms", "/_static/cms.js?v=m6")
loadModule("cstate", "/_static/cstate.js?v=m1")
loadModule("wsactions", "/_static/wsactions.js?v=m4")
loadModule("routers", "/_static/routers.js?v=m5") // Change this on router add/remove
loadModule("alert", "/_static/alert.js?v=256233234")

// Actual app code

docReady(function() {
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

