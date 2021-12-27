var rating = 0;
var slider = document.querySelectorAll(".range-slider");
// Update the current slider value (each time you drag the slider handle)
    for(var i = 0; i < slider.length; i++) {
	output_id = slider[i].getAttribute("output")
	document.getElementById(output_id).innerHTML = "Drag the slider to change your rating"; // Display the default slider value
	slider[i].oninput = function() {
		output = document.getElementById(this.getAttribute("output"))
		console.log(output)
		state = parseState(this.value)
		output.innerHTML = state + ", " + this.value;
	}
   }


function parseState(v) {
	state = ""
	if(v < 1)
		state = "Atrocity"
	else if(v < 2)
		state = "Absymal"
	else if(v < 3)
		state = "Really Poor"
	else if(v < 4)
		state = "Poor"
	else if(v < 5)
		state = "Below Average"
	else if(v < 6)
		state = "Average"
	else if(v < 7)
		state = "Above Average"
	else if(v < 8)
		state = "Meets Expectations"
	else if(v < 9)
		state = "Great"
	else if(v < 10)
		state = "Exceeds Expectations"
	else if(v == 10)
		state = "Without a doubt, perfect"
	return state
}

var ds = 0; // Whether the user is doing something
function botReviewEditPane(el, id) {
	rev = document.querySelector(`#reviewopt-${id}`)
	if(rev.style.display == "none" && ds == 0) {
		rev.style.display = 'block';
		el.innerHTML = 'Close';
		ds = 1;
		return
	}
	else if(ds == 1) {
		rev.style.display = 'none';
		el.innerHTML = 'Edit';
		ds = 0;
	}
}

function replyReview(el, id) {
	rev = document.querySelector('#reviewreply-' + id)
	if(rev.style.display == "none" && ds == 0) {
		rev.style.display = 'block';
		el.innerHTML = 'Close';
		ds = 2;
		return;
	}
	else if(ds == 2) {
		rev.style.display = 'none';
		el.innerHTML = 'Reply';
		ds = 0;
	}
}

function commandModal(id) {
	cmd = document.querySelector(`#cmd-${id}`).textContent
	cmd = JSON.parse(cmd)
	args = cmd.args.toString().replaceAll(",", " ")
	modalShow(`More information`, `
		Command: ${cmd.cmd_name}<br>
		Arguments: ${args.replaceAll(">", "</span>").replaceAll("<", "<span class='arg'>")}<br>
		Vote Locked: ${cmd.vote_locked}<br/>
		ID: ${cmd.id}<br/><br/>
		(Advanced) Raw JSON: ${JSON.stringify(cmd)}
	`) 
}

function getCommands(bot_id) {
	commandsTab = document.querySelector("#commands-tab")
	error = document.querySelector("#commands-error")
	request({
		url: `/api/bots/${context.id}/commands?lang=${context.site_lang}`,
		statusCode: {
			404: function(data) {
				error.textContent = "No Commands Found"
			},
			200: function(data_u) {
				sortjson = () => {data = Object.keys(data_u).sort().reduce(
					  (obj, key) => { 
						obj[key] = data_u[key]; 
						return obj;
					  }, 
					{}
				);
					return data
				}
				data = sortjson(data_u);
				commands = `<p style='font-size: 30px'>Commands List</p><p>Click on a category to expand/collapse it</p>`
				jQuery.each(data, function(group, gdata) {
					if(group == "default")
						group = "Miscellaneous" 
					commands += `
					<a class="white" style="font-size: 25px" aria-expanded="true" data-toggle="collapse" href="#${group}table">${group}</a>
					<section class="collapse show" id='${group}table' style="width: 100%">
					<table style="margin: 0 auto !important; width: 100%; table-layout: fixed;">
					<colgroup>
						<tr>
							<th style="border-right: none;">Name</th>
							<th style="border-right: none;">Description</th>
							<th style="border-right: none;">Docs</th>
							<th style="border-right: none;">Premium</th>
							<th style="border-right: none;">More</th>
						</tr>
					</colgroup>
				`
				/* TODO: Fill in HTML */
					gdata.forEach(function(cmd, i, a) {
							if(cmd.args.length == 0)
								cmd.args = ["No arguments"]
							if(cmd.doc_link.replaceAll(" ", "") == "")
								docs = "No docs available"
							else
								docs = `<a class='long-desc-link' href='${cmd.doc_link}'>Docs</a>`
							if(cmd.description.replaceAll(" ", "") == "" || cmd.description.length < 15)
								description = "There is no description available"
							else
								description = cmd.description
							commands += `
							<colgroup>
								<tr>
									<span style="display: none" id="cmd-${cmd.id}">${JSON.stringify(cmd)}</span>
									<td>${cmd.cmd_name}</td>
									<td>${description}</td>
									<td>${docs}</td>
									<td>${cmd.premium_only.toString().replace("true", "Yes").replace("false", "No")}</td>
									<td><a class='long-desc-link' href='javascript:void(0)' onclick="commandModal('${cmd.id}')">View</a>
							</tr>
						</colgroup>
						`
						});
					commands += `</table></section><br/>`
				});
				commandsTab.innerHTML = commands
			}
		}
	})
}

setTimeout(function(){getCommands(context.id)}, 700)

function deleteReview(rev_id) {
	request({
		method: 'DELETE',
		url: `/api/users/${context.user_id}/reviews/${rev_id}`,
		userAuth: true,
		statusCode: {
			200: function(data) {
				modalShow("Success!", "Deleted Review Successfully")
				window.location.refresh()
			}
		}	
	});
}



function voteReview(rev_id, upvote) {
	
	if(upvote) {
		vote_type = "upvote"
	}
	else {
		vote_type = "downvote"
	}	
	request({
		method: 'PATCH',
		url: `/api/users/${context.user_id}/reviews/${rev_id}/votes`,
		json: {"upvote": upvote},
		userAuth: true,
		statusCode: {
			200: function(data) {
				modalShow("Success!", `Successfully ${vote_type} this review`)
				setTimeout(() => window.location.reload(), 1500)
			}
		}
	});

}

function newReview(reply, root) {
	// Reply is a boolean signifying reply or not, root is the root review to reply on
	modalShow("Creating Review", "Please wait while Fates List adds your review...")
        
	rev_id = ''
	if(reply) {
           rev_id = `-${root}`
        }

	target_type = 0
	if(context.type == "server"){
		target_type = 1
	}

	review = document.querySelector(`#review${rev_id}`).value
	star_rating = document.querySelector(`#star_rating${rev_id}`).value
	request({
		method: 'POST',
		url: `/api/users/${context.user_id}/reviews`,
		json: {"reply": reply, "id": root, "review": review, "star_rating": star_rating, "target_id": context.id, "target_type": target_type},
		userAuth: true,
		statusCode: {
			200: function(data) {
				modalShow("Success", "Successfully created your review!")
				setTimeout(() => window.location.reload(), 1500)
			}
		}
	})
}

function editReview(id) {
	modalShow("Editting Review", "Please wait while Fates List edits your review...")
	star_rating = document.querySelector(`#r-${id}-edit-slider`).value
	review = document.querySelector(`#r-${id}-edit-text`).value
	request({
		method: 'PATCH',
		url: `/api/users/${context.user_id}/reviews/${id}`,
		json: JSON.stringify({"review": review, "star_rating": star_rating}),
		userAuth: true,
		statusCode: {
			200: function(data) {
				modalShow("Success", "Successfully editted your review!")
				setTimeout(() => window.location.reload(), 1500)
			}
		}
	})
}

function getReviewPage(page) {
	if(!page) {
		page = 1
	}
	document.querySelector("#review-write").innerHTML = "<h3 class='white'>Loading reviews...</h3>"
	request({
		url: `/${context.type}/${context.id}/reviews_html?page=${page}`,
		method: "GET",
		statusCode: {
			200: function(data) {
				document.querySelector("#review-write").innerHTML = data.responseText
				setTimeout(function() {document.querySelector("#rating-desc-avg").innerHTML = parseState(context.reviews.average_rating) + ", " + context.reviews.average_rating}, 5); 
			}
		}
	})
	context.rev_page = page
	jQuery(".page-item").removeClass("active")
	jQuery(`#page-${page}`).addClass("active")
}
