// The core launcher for Lynx

loadModule("doctree", "/_static/doctree.js?v=2")
loadModule("docs", "/_static/docs.js?v=m1")
loadModule("utils", "/_static/utils.js?v=m1")
loadModule("ws", "/_static/ws.js?v=m5")
loadModule("cms", "/_static/cms.js?v=m9")
loadModule("cstate", "/_static/cstate.js?v=m1")
loadModule("wsactions", "/_static/wsactions.js?v=m5")
loadModule("routers", "/_static/routers.js?v=m8") // Change this on router add/remove
loadModule("alert", "/_static/alert.js?v=m3")

readyModule("launcher")