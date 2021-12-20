function makeSmaller() {
	$('#msg').contents().unwrap().wrap("<h5 id='msg' class='text-center' style='color: red'></h5>");
}
function loginUser() {
	dev = localStorage.getItem("login-dev")
	retry = "<br/><br/><a href='https://fateslist.xyz/fates/login'>Try Again?</a>"
	searchParams = new URLSearchParams(window.location.search)
	error = searchParams.get("error")
	if(error) {
		makeSmaller()
		$("#msg").html("Login Cancelled" + retry)
		return
	}

	code = searchParams.get("code")
	state = searchParams.get("state")
	if(!code || !state) {
		makeSmaller()
		$("#msg").html("Invalid code/state" + retry)
		return
	}
	scopes = localStorage.getItem("login-scopes")
	if(!scopes) {
		makeSmaller()
		$("#msg").html("No scopes set" + retry)
		return
	}
	$.ajax({
		url: "/api/users",
		method: "POST",
		contentType: "application/json",
		data: JSON.stringify({"code": code, "scopes": JSON.parse(scopes)}),
		statusCode: {
			206: function(data) {
				localStorage.removeItem("login-scopes")
				if(dev) {
					makeSmaller()
					$("#msg").html(`Please copy the below into the app requesting auth: <br/><br/><code style='text-align: left !important'>${data.token}</code>`)
					localStorage.removeItem("login-dev")
				}
				else {
					window.location.href = localStorage.getItem("login-redirect")
				}
			},
			400: function(data) {
				makeSmaller()
				$("#msg").html(data.responseJSON.reason + retry)
			},
			403: function(data) {
				makeSmaller()
				banInfo = `
	      				<br/><br/>
					<p style="text-align: left !important; margin-left: 10em">
					You have been ${data.responseJSON.ban.type} banned.<br/>
					As a result, ${data.responseJSON.ban.desc}
	       				<br/><br/>
					<strong>Please click <a href="/fates/banappeal?token=${data.responseJSON.token}">here</a> or contact a Fates List Staff Member to appeal this ban</strong>
					</p>
					`
				$("#msg").html(data.responseJSON.reason + banInfo)
			},
			422: function(data) {
				makeSmaller()
				$("#msg").html("This script needs to be updated:<br/><code>" + JSON.stringify(data.responseJSON) + "</code>" + retry)
			},
			429: function(data) {
				makeSmaller()
				$("#msg").html(data.responseJSON.reason + retry)
			},
			500: function(data) {
				makeSmaller()
				$("#msg").html(`Internal Server Error<br/>Traceback:<br/><pre style="text-align: left !important">${data.responseJSON.traceback}</pre>` + retry)
			}
		}
	})
}
$(document).ready(
	function() {
		loginUser()
	}
)


