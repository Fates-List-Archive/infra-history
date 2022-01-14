function submitProfile() {
    context.error = null
    modalShow("Saving", "Please wait for a few moments while we save your profile")
    try {
	json = {user_id: context.bot.user.id}
	context.form_values.text.forEach(function (key) {
	    el = document.querySelector(`#${key}`)
	    json[key] = el.value
	    if(el.getAttribute("required") != null && !el.value){
		modalShow("Error", `You must enter a ${key.replaceAll("_", " ")} for your profile!`)
		context.error = key
		return
	    }
	})
	if(context.error) {
		return
	}
	context.form_values.select_single.forEach(function (key) {
	    json[key] = document.querySelector(`#${key}`).value
	})


	// For when multiple select pure is added
	toReplace = {
        }
	keys = []
	keys.forEach(function (key) {
	    json[key] = toReplace[key].filter(x => x !== "")
	})

	method = "PATCH"
	mod = "editted successfully!"
	context.form_values.select_multiple.forEach(function (key) {
		json[key] = document.querySelector(`#${key}`).values
	})
	request({
		url: `/api/users/${context.user_id}/preferences`,
		method: method,
		userAuth: true,
		json: json,
		statusCode: {
			200: function() {
				modalShow("Success", "Your profile has been " + mod + ". You will be redirected to it in a few moments")
				setTimeout(function(){
					window.top.location.replace(`/profile/${context.user_id}`)
				}, 1000);
			}
		}
	})
    }
    catch(err) {
    	alert(err)
    }
};

function showToken(but) {
	token = document.querySelector("#api-token")
	if(!token.getAttribute("show")) {
		token.innerHTML = context.real_user_token
		but.innerHTML = "Hide"
		token.setAttribute("show", "true")
	}
	else {
                token.innerHTML = "Click 'Show' to see your user token";
		but.innerHTML = "Show"
		token.removeAttribute('show')
	}
  }
  
function regenToken() {
	request({
	   userAuth: true,
	   method: 'PATCH',
	   url: `/api/users/${context.user_id}/token`
	});
	alert("Regenerated Token Successfully")
	window.top.location.reload()
}

function hideSaveOnAboutTab(id, evt, data) {
	if(id == "about" || id == "actions" || id == "analytics") {
		document.querySelector("#save-changes").style.display = "none"
	}
	else {
		document.querySelector("#save-changes").style.display = "initial"
	}
}

