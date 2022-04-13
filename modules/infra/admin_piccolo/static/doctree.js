function shadowsightTreeParse(tree) {
    if(addedDocTree) {
        info("Shadowsight", "Refusing to readd doctree")
        return
    }

    addedDocTree = true

    info("Shadowsight", "Trying to parse v2 doctree")
   
    ignore = ["privacy.md", "status-page.md", "index.md", "staff-guide.md"] // Index may be counter-intuitive, but we add this later

    treeDepthOne = []
    treeDepthTwo = {}

    tree.forEach(treeEl => {
        if(ignore.includes(treeEl[0])) {
            info("Shadowsight", "Ignoring unwanted tree element", treeEl[0])
            return
        }

        if(treeEl.length == 1) {
            treeDepthOne.push(treeEl[0].replace(".md", ""))
        } else if(treeEl.length == 2) {
            if(treeDepthTwo[treeEl[0]] === undefined) {
                treeDepthTwo[treeEl[0]] = []
            }
            treeDepthTwo[treeEl[0]].push(treeEl[1].replace(".md", ""))
        } else {
            error("Shadowsight", `Max nesting of 2 reached`)
        }
    })

    // Sort depth two alphabetically
    treeDepthTwo = Object.keys(treeDepthTwo).sort().reduce(
        (obj, key) => { 
          obj[key] = treeDepthTwo[key]; 
          return obj;
        }, 
        {}
    );

    // Sort values within depth one and two alphabetically
    for(let key in treeDepthTwo) {
        treeDepthTwo[key] = treeDepthTwo[key].sort()
    }

    treeDepthOne.sort(function(a, b){
        if(a>b) return 1;
        else return -1
    })

    // Readd index.md
    treeDepthOne.unshift("index")
      
    info("Shadowsight", `Parsed doctree:`, { treeDepthOne, treeDepthTwo })

    // Initial doctreeHtml
    doctreeHtml = `<li id="docs-main-nav" class="nav-item"><a href="#" class="nav-link"><i class="nav-icon fa-solid fa-book"></i><p>Docs and Blogs <i class="right fas fa-angle-left"></i></p></a><ul class="nav nav-treeview">`

    // First handle depth one
    treeDepthOne.forEach(el => {
        doctreeHtml += `<li class="nav-item"><a id="docs-${el}-nav" href="https://lynx.fateslist.xyz/docs/${el}" class="nav-link"><i class="far fa-circle nav-icon"></i><p>${title(el.replace("-", " "))}</p></a></li>`
    })

    for (let [tree, childs] of Object.entries(treeDepthTwo)) {
        doctreeHtml += `<li id="docs-${tree}-nav" class="nav-item"><a href="#" class="nav-link"><i class="nav-icon fa-solid fa-book"></i><p>${title(tree.replace("-", " "))} <i class="right fas fa-angle-left"></i></p></a><ul class="nav nav-treeview">`

        childs.forEach(child => {
            doctreeHtml += `<li class="nav-item"><a id="docs-${tree}-${child}-nav" href="https://lynx.fateslist.xyz/docs/${tree}/${child}" class="nav-link"><i class="far fa-circle nav-icon"></i><p>${title(child.replace("-", " "))}</p></a></li>`
        })

        doctreeHtml += "</ul></li>"
    }
    info("Shadowsight", "Doctree HTML: ", { doctreeHtml })

    $(doctreeHtml).insertBefore("#doctree")
}

readyModule("doctree")