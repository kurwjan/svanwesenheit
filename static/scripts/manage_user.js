function block(id) {
    document.getElementById("block-" + id).style.setProperty('display', 'none', 'important');
    document.getElementById("unblock-" + id).style.setProperty('display', 'flex', 'important');
}

function unblock(id) {
    document.getElementById("unblock-" + id).style.setProperty('display', 'none', 'important');
    document.getElementById("block-" + id).style.setProperty('display', 'flex', 'important');
}

function deactivate(id) {
    document.getElementById("reset_btn-" + id).disabled = true;
    document.getElementById("reset_btn-" + id).value = "Passwort zurückgesetzt";
}

function show(group_id, edit_group_id) {
    let group = document.getElementById(group_id);
    let edit_group = document.getElementById(edit_group_id)

    edit_group.style.display = "block";
    group.style.display = "none";
}

function hide(group_id, edit_group_id) {
    let group = document.getElementById(group_id);
    let edit_group = document.getElementById(edit_group_id)

    group.style.display = "block";
    edit_group.style.display = "none";
}