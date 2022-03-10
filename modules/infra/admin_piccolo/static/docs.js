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
    ws.send(JSON.stringify({request: "eternatus", feedback: feedback, page: window.location.pathname}))
}

async function genClientWhitelist() {
    reason = document.querySelector('#whitelist-reason').value

    if(reason.length < 10) {
        alert('Please enter a reason of at least 10 characters')
        return
    }

    privacy = document.querySelector('#privacy-policy').value

    if(privacy.length < 20) {
        alert('Please enter a privacy policy of at least 20 characters')
        return
    }

    client_info = document.querySelector('#client-info').value

    if(client_info.length < 10) {
        alert('Please enter a client info of at least 10 characters')
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
    ws.send(JSON.stringify({request: "data_request", user: userId}))
    document.querySelector("#request-btn").innerText = "Requesting..."
}