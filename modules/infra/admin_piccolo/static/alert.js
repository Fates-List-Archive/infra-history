let alerts = []

let intervals = []

function alert(id, title, content) {
    if(id === "fatal-error") {
        intervals.forEach(interval => {
            clearInterval(interval)
            intervals.splice(intervals.indexOf(interval), 1)
        })
        alerts = [id];
    } else {
        if(alerts.length > 0) {
            intervals.push(setTimeout(() => {
                alert(id, title, content)
            }, 300))
            return
        }
        alerts.push(id)
        intervals.forEach(interval => {
            clearInterval(interval)
            intervals.splice(intervals.indexOf(interval), 1)
        })
    }
    $("#alert-placer").html(`
<dialog 
    id="${id}"
    open 
    role='dialog'
    aria-labelledby="${id}-title"
    aria-describedby="${id}-content"  
>
    <section>
    <header id="${id}-title">
        <strong>
        <h2 class="alert-title">${title}</h2>
        </strong>
    </header>

    <div id="${id}-content">
        ${content}
    </div>
    <button onclick="closeAlert()" id="alert-close" class="block mx-auto">
        Close
    </button>
    </section>
</dialog>
  
<style>
    dialog {
    position: fixed;
    top: 0;
    right: 0;
    left: 0;
    bottom: 0;
    z-index: 9999;
    height: 100%;
    width: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    background: transparent; 
    color: black !important; 
}
dialog::after {
    content: '';
    display: block;
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
    background: black;
    opacity: .5;
    z-index: -1;
    pointer-events: none;
}
section {
    width: 500px;
    min-height: 200px;
    max-height: 500px;
    padding: 10px;
    border-radius: 4px 4px 4px 4px;
    background: white;
}
#alert-close {
    position: relative;
    text-align: center !important;
    top: 0 !important;
    bottom: 0 !important;
}
.alert-title {
    color: black !important;
}

#alert-close {
    background-color: white !important;
    color: black !important;
    font-weight: bold !important;
    border: black solid 1px !important;
    margin-top: 3px;
    padding: 10px;
}

block {
    display: block;
}
</style>
    `)
}

function closeAlert() {
    alerts.forEach(id => {
        $(`#${id}`).remove()
        alerts.splice(alerts.indexOf(id), 1)
    })
}

window.alert = alert

readyModule("alert")