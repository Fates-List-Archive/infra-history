function addUserToExp() {
    var exp = document.querySelector("#exp_add-value").value
    var id = document.querySelector('#exp_add-id').value;

    wsSend({request: "exp_rollout_add", id: id, exp: exp})
}

function delUserFromExp() {
    var exp = document.querySelector("#exp_del-value").value
    var id = document.querySelector('#exp_del-id').value;

    wsSend({request: "exp_rollout_del", id: id, exp: exp})
}

function rolloutExp() {
    let v = prompt("This will rollout the experiment to all users. Are you sure you want to do this? Type 'Catnip' to rollout")

    if(v !== "Catnip") {
        return
    }

    var exp = document.querySelector("#exp_rollout-value").value

    wsSend({request: "exp_rollout_all", exp: exp})
}

function rolloutExpUndo() {
    let v = prompt("This will undo rollout of the experiment to all users. Are you sure you want to do this? Type 'Catnip' to undo rollout")

    if(v !== "Catnip") {
        return
    }

    var exp = document.querySelector("#exp_rollout_undo-value").value

    wsSend({request: "exp_rollout_undo", exp: exp})
}

function rolloutControlled() {
    var exp = document.querySelector("#exp_rollout_controlled-value").value
    var limit = document.querySelector("#exp_rollout_controlled-limit").value

    wsSend({request: "exp_rollout_controlled", exp: exp, limit: limit})
}

readyModule("exp-rollout")