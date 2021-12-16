function voteBot() {
	if(context.type == "server") {
		modalShow("Voting for servers", "Do /vote in this server to vote for it and get exclusive perks if the server supports vote rewards")
		return
	}
	if(!context.logged_in) {
		window.location.href = `/fates/login?redirect=/${context.type}/${context.id}/vote&pretty=to vote for this bot`
		return
	}
	modalShow("Sending your vote", "Please wait...")
	request({
		url: `/api/dragon/bots/${context.id || context.bot_id}/votes`,
		json: {user_id: context.user_id, test: context.mode == "edit"},
		method: "PATCH",
		userAuth: true,
		statusCode: {
			200: function(data) {
				if(context.mode == "edit") modalShow("Sent test vote successfully!", "Check your webhook handler now!")
				else {
					modalShow("Vote Succesful!", "You have successfully voted for this bot!")
					setTimeout(() => (window.location.href = `/${context.type}/${context.id}`), 1500)
				}
			}
		}
	})
}
