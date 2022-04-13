async function loadDocs() {
    hljs.highlightAll();
    window.highlightJsBadge();

    $("<div id='toc'></div>").insertAfter("#feedback-div")

    document.querySelectorAll(".header-anchor").forEach(el => {
        // Add el to table of contents
        data = el.previousSibling.data
        if(
            data.startsWith("GET")
            || data.startsWith("POST")
            || data.startsWith("PUT")
            || data.startsWith("PATCH")
            || data.startsWith("DELETE")
            || data.startsWith("HEAD")
            || data.startsWith("OPTIONS")
            || data.startsWith("PPROF")
            || data.startsWith("WS")
        ) {
            return
        }

        $(`<a href='${el.href}'>${el.previousSibling.data}</a></br/>`).appendTo("#toc");
    })
}

async function rateDoc() {
    feedback = document.querySelector("#doc-feedback").value
    wsSend({request: "eternatus", feedback: feedback, page: window.location.pathname})
}

async function genClientWhitelist() {
    reason = document.querySelector('#whitelist-reason').value

    if(reason.length < 10) {
        alert("whitelist-res", "Whoa there!", 'Please enter a reason of at least 10 characters')
        return
    }

    privacy = document.querySelector('#privacy-policy').value

    if(privacy.length < 20) {
        alert("whitelist-res", "Whoa there!", 'Please enter a privacy policy of at least 20 characters')
        return
    }

    client_info = document.querySelector('#client-info').value

    if(client_info.length < 10) {
        alert("whitelist-res", "Almost done...", 'Please enter a client info of at least 10 characters')
        return
    }

    var encodedString = btoa(JSON.stringify({
        reason: reason,
        privacy: privacy,
        client_info: client_info,
    }));
    document.querySelector("#verify-screen").innerHTML = `<h3>Next step</h3><p>Copy and send <code style='display: inline'>${encodedString}</code> to any Head Admin+ to continue</p>`
}

async function dataRequest() {
    userId = document.querySelector("#user-id").value
    wsSend({request: "data_request", user: userId})
    document.querySelector("#request-btn").innerText = "Requesting..."
}

async function dataDelete() {
    let confirm = prompt("Are you sure you want to delete all data? This cannot be undone. Please read all warnings carefully. This may in the future trigger a webhook to all bots you have voted for.\n\nType 'DELETE-POPPYPAW' to confirm.")
    if(confirm !== "DELETE-POPPYPAW") {
        alert("del-res", "Aborted", "Aborted data deletion")
        return
    }
    userId = document.querySelector("#user-id-del").value
    wsSend({request: "data_deletion", user: userId})
}

readyModule("docs")
