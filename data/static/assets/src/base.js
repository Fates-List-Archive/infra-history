// When the user scrolls down 20px from the top of the document, show the button
window.onscroll = function () {
  upbtn = document.querySelector("#up-btn");
  if (document.body.scrollTop > 50 || document.documentElement.scrollTop > 50) {
		upbtn.style.display = "block";
  } 
  else {
		upbtn.style.display = "none";
  }
}

// When the user clicks on the button, scroll to the top of the document
function topFunction() {
  document.body.scrollTop = 0; // For Safari
  document.documentElement.scrollTop = 0; // For Chrome, Firefox, IE and Opera
}

function modalShow(title, body) {
	alert(`${title}: ${body}`)
}


function request(data) {
  window.reqData = data
  if(!data.statusCode) {
    data.statusCode = {}
  }

  if(!data.statusCode[429]) {
    data.statusCode[429] = function(d) {
      if(!reqData.rlText) {
        data.rlText = d.responseJSON.reason
      }
      if(!reqData.rlTitle) {
        data.rlTitle = "Ratelimited"
      }
      modalShow(reqData.rlTitle, reqData.rlText)
    }
  }
  if(!data.statusCode[422]) {
    data.statusCode[422] = function(d) {
      json = JSON.stringify(data.responseJSON)
      modalShow("An error occurred during initial proccessing. Try again later", json)
    }
  }
  if(!data.statusCode[404]) {
    data.statusCode[404] = function() {
      modalShow("API is down", "Unfortunately, the Fates List API is down right now (or the resource you are looking for no longer exists). Please try again later")
    }
  }
  if(!data.statusCode[400]) {
    data.statusCode[400] = function(d) {
      if(!reqData.errTitle) {
        reqData.errTitle = "Error"
      }
      modalShow(reqData.errTitle, d.responseJSON.reason)
    }
  }
  if(!data.statusCode[500]) {
    data.statusCode[500] = function() {
      modalShow("Internal Server Error", "We had an error internally on our side when proccessing your request. Please try again later.")
    }
  }

  if(!data.headers) {
    data.headers = {}
  }

  if(data.userAuth) {
    data.headers["Authorization"] = context.user_token
  }
  else if(data.botAuth) {
    data.headers["Authorization"] = context.bot_token
  }

  jQuery.ajax({
    		url: data.url,
		method: data.method,
		dataType: "json",
		processData: false,
		contentType: 'application/json',
		data: JSON.stringify(data.json || data.data),
		headers: data.headers,
    		statusCode: data.statusCode
  })
}

// Set current page
if(!context.login_page) {
  localStorage.setItem("current-page", window.location.href)
}

String.prototype.replaceAll = function(strReplace, strWith) {
  // See http://stackoverflow.com/a/3561711/556609
  var esc = strReplace.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
  var reg = new RegExp(esc, 'ig');
  return this.replace(reg, strWith);
}

String.prototype.replacem = function(replaceList) {
  var new_str = this
  for(var i = 0; i < replaceList.length; i++) {
    new_str = new_str.replaceAll(replaceList[i][0], replaceList[i][1])
  }
  return new_str;
}

String.prototype.replaceAllBackup = function(str, newStr){
		if (Object.prototype.toString.call(str).toLowerCase() === '[object regexp]') {
			return this.replace(str, newStr);
		}
		return this.replace(new RegExp(str, 'g'), newStr);
};
