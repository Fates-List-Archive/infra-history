docReady(() => {
    hljs.highlightAll();
    window.highlightJsBadge();
})

async function rateDoc() {
    feedback = document.querySelector("#doc-feedback").value
    let res = await fetch("/_eternatus", {
        method: "POST",
        credentials: 'same-origin',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            "feedback": feedback,
            "page": window.location.pathname
        }),
    })
    let json = await res.json()
    alert(json.detail)
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