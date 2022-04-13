function sendUserAction(name, userId, reason, context="") {
    wsSend({
        request: "user_action", 
        action: name, 
        action_data: {
            user_id: userId, 
            reason: reason, 
            context: context,
        }
    })
}

async function addStaff() {
    let userId = document.querySelector("#staff_user_id").value
    sendUserAction("add_staff", userId, "STUB_REASON")
}

async function deleteAppByUser(userID) {
    confirm("Are you sure you want to delete this and all application belonging to this user?")
    sendUserAction("ack_staff_app", userID, "STUB_REASON")
}

// TODO: This does not yet exist!
async function setUserState() {
    let userId = document.querySelector("#user_state_id").value
    let state = document.querySelector("#user_state_select").value
    let reason = document.querySelector("#user_state_reason").value
    sendUserAction("set_user_state", userId, reason, parseInt(state))
}

readyModule("user-actions")