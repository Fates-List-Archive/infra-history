// A set of form validators for lynx (apply.js because its *applying* validation)

async function applyForStaff() {
    let answers = {}

    let questions = document.querySelectorAll(".question")

    questions.forEach(question => {
        answers[question.id] = question.value
    })

    wsSend({
        request: "apply_staff", 
        answers: answers
    })
}

async function loaSend() {
  let answers = {}

  let questions = document.querySelectorAll(".question")

  questions.forEach(question => {
      answers[question.id] = question.value
  })

  wsSend({
      request: "send_loa", 
      answers: answers
  })
}

// Example starter JavaScript for disabling form submissions if there are invalid fields
(function () {
    'use strict'
  
    // Fetch all the forms we want to apply custom Bootstrap validation styles to
    var forms = document.querySelectorAll('.needs-validation')
  
    // Loop over them and prevent submission
    Array.prototype.slice.call(forms)
      .forEach(function (form) {
        form.addEventListener('submit', function (event) {
          if (!form.checkValidity()) {
            event.preventDefault()
            event.stopPropagation()
          } else {
              if(window.location.pathname.startsWith("/apply")) {
                applyForStaff()
              } else if (window.location.pathname.startsWith("/loa")) {
                loaSend()
              }
              event.preventDefault()
              event.stopPropagation()
          }
  
          form.classList.add('was-validated')
        }, false)
      })
  })()  

  readyModule("apply")