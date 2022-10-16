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

function explanation(selected) {
    let type_selector = document.getElementById("explanation")

    if (selected.value === "Admin") {
        type_selector.textContent = "Als Admin kann man neue Sitzungen und Benutzer erstellen/bearbeiten."
    }
    else if (selected.value === "Bearbeiter") {
        type_selector.textContent = "Man kann das gleiche wie ein Admin machen außer Benutzer verwalten."
    }
    else {
        type_selector.textContent = "Als Nutzer kann man die Anwesenheitslisten etc. sehen."
    }
}