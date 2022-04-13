// Minify using https://jscompress.com/ and ES2022

// Not a module, should never be loaded as one

// Custom logger
const log = (...args) => {
    console[args[0]](`%c[${Date.now()}]%c[${args[1]}]%c`, "color:red;font-weight:bold;", "color:purple;font-weight:bold;", "", ...args.slice(2))
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
modules = {}

function readyModule(name) {
    info("StarClan", `Module: ${name} has loaded successfully!`)
    modulesLoaded.push(name)
}

function loadModule(name, path, callback = () => {}) {
    if(modulesLoaded.includes(name)) return;
    modules[name] = path
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

// Load launcher
loadModule("launcher", "/_static/launcher.js?v=m1")
