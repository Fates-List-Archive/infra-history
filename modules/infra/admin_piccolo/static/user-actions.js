function sendUserAction(name, userId, reason) {
    ws.send(JSON.stringify({
        request: "user_action", 
        action: name, 
        action_data: {
            user_id: userId, 
            reason: reason, 
            csrf_token: csrfToken
        }
    }))
}

async function addStaff() {
    let userId = document.querySelector("#staff_user_id").value
    sendUserAction("add_staff", userId, "STUB_REASON")
}

async function deleteAppByUser(userID) {
    confirm("Are you sure you want to delete this and all application belonging to this user?")
    sendUserAction("ack_staff_app", userID, "STUB_REASON")
}