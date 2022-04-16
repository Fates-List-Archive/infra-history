// Stores the lynx state in one place
if(!localStorage.ackedMsg) {
    localStorage.ackedMsg = JSON.stringify([])
}

var ackedMsg = JSON.parse(localStorage.ackedMsg);
var pushedMessages = [];

var forcedStaffVerify = false

var inDocs = false
var addedDocTree = false
var havePerm = false
var staffPerm = 1
var alreadyUp = false
var refresh = false
var adminPatchCalled = false

var currentLoc = window.location.pathname
var hasLoadedAdminScript = false
var perms = {name: "Please wait for websocket to finish loading", perm: 0}
var user = {id: "0", username: "Please wait for websocket to finish loading"}
var assetList = {};

var experiments = [];

contentLoadedOnce = false
contentCurrPage = window.location.pathname
waitInterval = -1
myPermsInterval = -1

readyModule("cstate")