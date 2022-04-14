["info", "debug", "warn", "error"].forEach(level => {
    window[level] = function(...args) {
        parent.window[level]("Poppypaw", ...args)
    }
})

// Patch fetch (though not XHR)
window.fetchOrig = window.fetch

window.fetch = async (...args) => {
    info("Poppypaw", "Fetching", ...args)
    return await window.fetchOrig(...args)
}

info("Poppypaw", "Injected JS into iframe was success")