function submitBot() {
    try {
	json = {}
	errorFields = []
	context.form_values.text.forEach(function (key) {
	    el = document.querySelector(`#${key}`)
	    json[key] = el.value
	    if(el.getAttribute("required") != null && !el.value){
		errorFields.push(key.replaceAll("_", " "))
		return
	    }
	})

	if(errorFields.length > 0) {
		modalShow("Error", `You must enter a ${errorFields.join(', ')} for your bot!`)
		return
	}

	context.form_values.select_single.forEach(function (key) {
	    json[key] = document.querySelector(`#${key}`).value
	})

    	tags = document.querySelector("#tags").values
	toReplace = {
	    tags: document.querySelector("#tags").values,
	    extra_owners: json.extra_owners.replace(" ", "").split(","),
            features: document.querySelector("#features").values
        }
	keys = ["extra_owners", "tags", "features"]
	keys.forEach(function (key) {
	    json[key] = toReplace[key].filter(x => x !== "")
	})
	if(context.mode == "edit") {
	    json.bot_id = context.bot_id
	    method = "PATCH"
	    mod = "editted successfully!"
	}
	else {
	    method = "PUT"
	    mod = "added to our queue"
	}
	context.form_values.select_multiple.forEach(function (key) {
		json[key] = document.querySelector(`#${key}`).values
	})
	if(json.tags.length == 0 || json.tags[0] == "") {
	    modalShow("Error", "You need to select tags for your bot!")
	    return
	}
	request({
		url: `/api/users/${context.user_id}/bots/${json.bot_id}`,
		method: method,
		userAuth: true,
		json: json,
		statusCode: {
			200: function() {
				modalShow("Success", "Your bot has been " + mod + ". You will be redirected to it once you dismiss this alert")
				window.top.location.replace(`https://fateslist.xyz/bot/${json.bot_id}`)
			}
		}
	})
    }
    catch(err) {
    	alert(err)
    }
};

function deleteBot() {
	bot_id_prompt = prompt("In order to confirm your request, please enter the Bot ID for your bot", "")
	if(!bot_id_prompt || bot_id_prompt != context.bot_id) {
             	// User did not type proper bot id
		modalShow("Failed to delete bot", "This bot couldn't be deleted as you did not confirm that you wanted to do this!")
		return
	}
	modalShow("Deleting Bot..", "Please wait...")
	request({
		url: `/api/users/${context.user_id}/bots/${context.bot_id}`,
		method: "DELETE",
		userAuth: true,
		statusCode: {
			202: function(data) {
				modalShow("Bot Deleted :(", "This bot has been added to our queue of bots to delete and will be deleted in just a second or two")
				setTimeout(setInterval(function(){
				request({
					url: `/api/bots/${context.bot_id}`,
					method: "GET",
					statusCode: {
						404: function(data){
							window.top.location.replace(`/`)
						}
					}
				})
				}, 2000), 1000);
			},
		}
	})
}

function showToken(but) {
	token = document.querySelector("#api-token")
	if(!token.getAttribute("show")) {
		token.innerHTML = context.bot_token
		but.innerHTML = "Hide"
		token.setAttribute("show", "true")
	}
	else {
        token.innerHTML = "Click 'Show' to see your bots token";
		but.innerHTML = "Show"
		token.removeAttribute('show')
	}
  }
  function postStats() {
	server_count = document.querySelector("#server-count").value
  	payload = {"guild_count": server_count}
	request({
		botAuth: true,
		method: 'POST',
		url: `/api/bots/${context.bot_id}/stats`,
		json: payload
	});
	modalShow("Success", "Done posting stats. You may leave this page or continue editing this bot!")
  }
  function regenToken() {
	request({
	   botAuth: true,
	   method: 'PATCH',
	   url: `/api/bots/${context.bot_id}/token`
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

// Analytics
var ws = null
var cache = {"btl": {"username": "Unknown, bot too large"}}

function listenAnalytics() {
	if(ws) {
		ws.close(1015)
	}
	document.querySelector("#output-analytics").textContent = ""
	ws = new FatesWS(context.bot_id, context.bot_token, true, false, true)
	ws.hooks.event = async function(cls, data) {
		if(data.chan == "global") return; // Global channel is not yet implemented
		let eStr = JSON.stringify(data.dat)
		console.log(Events, data.dat.m.e)
		let userStr = data.dat.ctx.user
		if(userStr === "0") {
			userStr = "Anonymous/Not logged in"
		} else {
			if(context.votes > 3000) {
				userObj = cache["btl"]
			} else {
				userObj = cache[data.dat.ctx.user]
				if(!userObj) {
					res = await fetch(`${context.site_url}/api/users/${data.dat.ctx.user}/obj`)
					cache[userkey] = await res.json()
					userObj = cache[userkey]
				}
			}
			userStr = `${userObj.username} (${data.dat.ctx.user})`
		}
		let tsDate = new Date(data.dat.m.ts * 1000);
		let tsStr = `${tsDate} (timestamp ${data.dat.m.ts})`
		if(data.dat.m.e == Events.ViewEvent) {
			eStr = `User (${userStr}) is viewing your bot at ${tsStr}`
		} else if (data.dat.m.e == Events.InviteEvent) {
			eStr = `User (${userStr}) is interested in your bot and has clicked the 'Invite' button at ${tsStr}`
		} else if (data.dat.m.e == Events.VoteEvent) {
			eStr = `User (${userStr}) has voted for your bot and your bot now has ${data.dat.ctx.votes} votes!`
		}
		document.querySelector("#output-analytics").textContent += "\n\n" + eStr
	}
	ws.start()
}

function submitAppeal() {
	modalShow("Sending appeal...", "Please wait while Fates List sends your appeal real quick!")
	appeal = document.querySelector("#appeal").value
	if(appeal.length < 7) {
		modalShow("Error", "Your appeal must be at least 7 characters long")
		return
	}
	request({
		url: `/api/users/${context.user_id}/bots/${context.bot_id}/appeal`,
		method: "POST",
		userAuth: true,
		json: {"appeal": appeal},
		statusCode: {
			200: function() {
				modalShow("Success", "Done posting appeal. Please wait while our staff reviews it!")
				setTimeout(function(){window.location.replace(`/bot/${context.bot_id}`)}, 3000)
			},
		}
	})
}

function autofillBot() {
	function qs(q) {
		return document.querySelector(q)
	}
	bot_id = qs("#bot_id").value
	if(!bot_id) {
		return
	}
	jQuery.ajax({
		method: "GET",
		url: `https://discord.com/api/v9/applications/${bot_id}/rpc`,
		statusCode: {
			200: function(data) {
				if(!data.bot_public) {
					modalShow("Cannot autofill", "This bot is not a public bot")
					return
				}
				if(data.description) qs("#description").value = data.description
				if(data.summary) qs("#long_description").textContent = data.summary
				if(data.privacy_policy_url) qs("#privacy_policy").value = data.privacy_policy_url
				if(data.custom_install_url) qs("#invite").value = data.custom_install_url
				if(data.slug) qs("#vanity").value = data.slug.toLowerCase()
				else qs("#vanity").value = data.name.replaceAll(" ", "").toLowerCase()
				modalShow("Autofill Done", "We've autofilled as much of what we could find on your bots application!")
			},
			404: function(data) {
				modalShow("This bot does not exist!", "Please check the bot id you inputted")
			}

		}
	})

}


function transferOwnership() {
	new_owner = document.querySelector("#new-owner").value
	if(!new_owner) {
		modalShow("Error", "No new owner was specified")
		return
	}

	bot_id_prompt = prompt("In order to confirm your request, please enter the Bot ID for your bot", "")
	if(!bot_id_prompt || bot_id_prompt != context.bot_id) {
        // User did not type proper bot id
		modalShow("Failed to transfer bot ownership", "This bot couldn't be transferred as you did not confirm that you wanted to do this!")
		return
	}
	modalShow("Transferring bot ownership..", "Please wait...")
	request({
		url: `/api/users/${context.user_id}/bots/${context.bot_id}/ownership`,
		method: "PATCH",
		json: {"new_owner": new_owner},
		userAuth: true,
		statusCode: {
			200: function() {
				modalShow("Success", "Transferred bot ownership successfully")
				setTimeout(function(){window.location.replace(`/bot/${context.bot_id}`)}, 3000)
			},
			404: function(data) {
				modalShow("Error", "This bot could not be found. Has it been deleted?")
			},
		}
	})
}
