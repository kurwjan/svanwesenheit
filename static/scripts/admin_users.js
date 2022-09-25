function remove_card(id) {
    document.getElementById(id).style.display = "none";
}

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