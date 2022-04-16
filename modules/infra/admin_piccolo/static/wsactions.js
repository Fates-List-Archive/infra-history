actions = {
    "user_info": (data) => {
        user = data.user
    },
    "cfg": (data) => {
        info("Silverpelt", "Got server config. Applying...")
        assetList = data.assets
        wsContentResp = new Set(data.responses)
        wsContentSpecial = new Set(data.actions)
        experiments = UserExperiments.from(data.experiments)
        shadowsightTreeParse(data.tree)
    },
    "spld": (data) => {
        debug("Silverpelt", `Got a spld (server pipeline) message: ${data.e}`)
        if(data.e == "M") {
            info("Silverpelt", "Server is in maintenance mode. Alerting user to this")
            alert("maint", "Maintenance", "Lynx is now down for maintenance, certain actions may be unavailable during this time!")
        } else if(data.e == "RN") {
            info("Silverpelt", "Server says refresh is needed")
            if(!data.loc || data.loc == currentLoc) {
                refreshPage()
            } else {
                info("Silverpelt", "Refresh does not pertain to us!")
            }
        } else if(data.e == "MP") {
            info("Silverpelt", "Server says we do not have the required permissions")
            loadContent(`/missing-perms?min-perm=${data.min_perm || 2}`)
        } else if(data.e == "OD") {
            info("Silverpelt", "Client out of date.")
            wsFatal = true
            alert("nonce-err", "Hmmm...", "Your Lynx client is a bit out of date. Consider refreshing your page?")
        } else if(data.e == "VN") {
            info("Silverpelt", "Staff verify required")
            if(currentLoc == "/staff-guide") {
                debug("Silverpelt", "Staff guide is open, not redirecting")
                return
            }
            loadContent("/staff-verify")
        } else if(data.e == "U") {
            info("Silverpelt", "Unsupported action")
            alert("nonce-err", "Whoa!", "This action is not quite supported at this time")
        } else if(data.e == "P") {
            debug("Silverpelt", "Ping event. Going home...")
            $("#ws-info").text(`Websocket still connected as of ${Date()}`)
        }
    },
    "notifs": (data) => {
        info("Silverpelt", "Got notifications, loading Bramblestar")
        data.data.forEach(function(notif) {
            // Before ignoring acked message, check if its pushed
            if(!pushedMessages.includes(notif.id)) {
                // Push the message
                debug("Bramblestar", `${notif.id} is not pushed`)
                notifCount = parseInt(document.querySelector("#notif-msg-count").innerText)
                debug("Bramblestar", `Notification count is ${notifCount}`)
                document.querySelector("#notif-msg-count").innerText = notifCount + 1

                $(`<a href="#" class="dropdown-item"><i class="fas fa-envelope mr-2"></i><span class="float-right text-muted text-sm">${notif.message}</span></a>`).insertBefore("#messages")

                pushedMessages.push(notif.id)
            }

            if(notif.acked_users.includes(data.user_id)) {
                return;
            } else if(ackedMsg.includes(notif.id)) {
                debug("Bramblestar", `[Bramblestar] Ignoring acked message: ${notif.id}`)
                return;
            }

            if(notif.type == 'alert') {
                alert(`notif-urgent`, "Urgent Notification", notif.message);
                ackedMsg.push(notif.id)
                localStorage.ackedMsg = JSON.stringify(ackedMsg);
            }
        })
    },
    "perms": (data) => {
        $("#ws-info").html(`Websocket perm update done to ${data.data}`)
        havePerm = true
        info("Nightheart", "Got permissions")
        perms = data.data
        staffPerm = data.data.perm

        // Remove admin panel
        if(staffPerm >= 2) {
            if(!hasLoadedAdminScript) {
                loadModule("admin-nav", assetList["admin-nav"], () => {
                    hasLoadedAdminScript = true
                })
            } else {
                loadAdmin()
            }
            $('.admin-only').css("display", "block")
        }
        setInterval(() => {
            if(staffPerm < 2) {
                $(".admin-only").css("display", "none")
            }
        })
    },
    "reset": (_) => {
        $("#ws-info").html(`Websocket cred-reset called`)
        info("Nightheart", "Credentials reset")
        
        // Kill websocket
        ws.close(4999, "Credentials reset")
        document.querySelector("#verify-screen").innerHTML = "Credential reset successful!"
    },
    "cosmog": (data) => {
        if(data.pass) {
            alert("success-verify", "Success!", data.detail)
            document.querySelector("#verify-screen").innerHTML = `<h4>Verified</h4><pre>Your lynx password is ${data.pass}</pre><br/><div id="verify-parent"><button id="verify-btn" onclick="window.location.href = '/'">Open Lynx</button></div>`
        } else {
            alert("fail-verify", "Verification Error!", data.detail)
            document.querySelector("#verify-btn").innerText = "Verify";    
        }
    },
    "data_request": (data) => {
        info("Nightheart", "Got data request")
        if(data.detail) {
            alert("data-del", "Data deletion error", data.detail)
            document.querySelector("#request-btn").innerText = "Request"
            return
        } else if(data.data) {
            downloadTextFile(data.data, `data-request-${data.user}.fates`)
            hljs.highlightAll();
            window.highlightJsBadge();
            document.querySelector("#request-btn").innerText = "Requested"
            document.querySelector("#request-btn").ariaDisabled = true
            document.querySelector("#request-btn").setAttribute("disabled", "true")
        }
    },
    "experiments": (data) => {
        console.log("Got experiments")
        experiments = UserExperiments.from(data.experiments)
    }
}

readyModule("wsactions")