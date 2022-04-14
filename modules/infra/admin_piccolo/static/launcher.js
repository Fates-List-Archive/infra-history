// The core launcher for Lynx
const launcherVer = "ashfur-v1"

loadModule("cstate", "/_static/cstate.js?v=m4")
loadModule("doctree", "/_static/doctree.js?v=m2")
loadModule("docs", "/_static/docs.js?v=m1")
loadModule("utils", "/_static/utils.js?v=m1")
loadModule("ws", "/_static/ws.js?v=m21")
loadModule("cms", "/_static/cms.js?v=m59")
loadModule("wsactions", "/_static/wsactions.js?v=m85")
loadModule("routers", "/_static/routers.js?v=m41") // Change this on router add/remove
loadModule("alert", "/_static/alert.js?v=m3")

function lynxInfo() {
    info("Dark Forest", `Lynx Launcher Version: ${launcherVer}`, { modules, modulesLoaded })

    return {"launcherVer": launcherVer, "modules": modules, "modulesLoaded": modulesLoaded}
}

lynxInfo()

readyModule("launcher")