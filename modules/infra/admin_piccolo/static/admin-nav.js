var adminLoaded = false

function loadAdmin() {
    if(adminLoaded) {
        return
    }
    $(`
    <li class="nav-item d-none d-sm-inline-block admin-only">
    <a href="https://lynx.fateslist.xyz/admin" class="nav-link admin-only">Admin</a>
  </li>
  <li class="nav-item d-none d-sm-inline-block admin-only">
    <a href="https://lynx.fateslist.xyz/bot-actions" class="nav-link admin-only">Bot Actions</a>
  </li>
  <li class="nav-item d-none d-sm-inline-block admin-only">
    <a href="https://lynx.fateslist.xyz/user-actions" class="nav-link admin-only">User Actions</a>
  </li>
    `).insertAfter("#home-link")

    $(`
  <li class="nav-item admin-only">
    <a id="staff-apps-nav" href="https://lynx.fateslist.xyz/staff-apps" class="nav-link">
    <i class="nav-icon fa-solid fa-rectangle-list"></i>
      <p>Staff Applications</p>
    </a>
  </li>
  <li class="nav-item admin-only" id="lynx-admin-nav">
    <a href="https://lynx.fateslist.xyz/admin" class="nav-link">
    <i class="nav-icon fa-solid fa-server"></i>
      <p>Piccolo Admin</p>
    </a>
  </li>
  <li class="nav-item admin-only">
    <a id="loa-nav" href="https://lynx.fateslist.xyz/loa" class="nav-link">
    <i class="nav-icon fa-solid fa-baby-carriage"></i>
      <p>Leave Of Absence</p>
    </a>
  </li>
    `).insertAfter("#staff-guide-nav-li")

    $(`
  <li id="admin-panel-nav" class="nav-item admin-only">
    <a id="admin-panel-nav-link" href="#" class="nav-link">
      <i class="nav-icon fa-solid fa-candy-cane"></i>
      <p>Admin Panel <i class="right fas fa-angle-left"></i></p>
    </a>
    <ul class="nav nav-treeview">
      <li class="nav-item">
        <a id="bot-actions-nav" href="https://lynx.fateslist.xyz/bot-actions" class="nav-link">
        <i class="far fa-circle nav-icon"></i>
          <p>
            Bot Actions
            <span class="right badge badge-info">Beta</span>
          </p>
        </a>
      </li>
      <li class="nav-item">
        <a id="user-actions-nav" href="https://lynx.fateslist.xyz/user-actions" class="nav-link"
          ><i class="far fa-circle nav-icon"></i>
          <p>
            User Actions
            <span class="right badge badge-info">Beta</span>
          </p></a
        >
      </li>
    </ul>
  </li>
    `).insertAfter("#links-nav-li")
    $('.admin-only').css("display", "block")
    adminLoaded = true
}

$(loadAdmin)

readyModule("admin-nav")