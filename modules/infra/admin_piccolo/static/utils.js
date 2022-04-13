function downloadTextFile(text, name) {
    const a = document.createElement('a');
    const type = name.split(".").pop();
    a.href = URL.createObjectURL( new Blob([text], { type:`text/${type === "txt" ? "plain" : type}` }) );
    a.download = name;
    a.click();
}  

// https://stackoverflow.com/a/46959528
function title(str) {
    return str.replaceAll("-", " ").replaceAll("_", " ").replace(/(^|\s)\S/g, function(t) { return t.toUpperCase() });
}

readyModule("utils")