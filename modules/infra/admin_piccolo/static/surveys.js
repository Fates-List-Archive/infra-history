function submitSurvey(id, questions) {
    let answers = {}
    let error = false
    questions.forEach(question => {
        if(error) {
            return
        }
        let answer = document.querySelector(`#${question}`).value
        if(answer.length < 6) {
            alert("submit-res", "Whoa there!", `Please answer the question "${question}" with at least 6 characters`)
            error = true
            return
        }
        answers[question] = answer
    })
    if(error) {
        return
    }

    wsSend({request: "survey", id: id, answers: answers})
}

readyModule("surveys")