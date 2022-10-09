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

function explanation(selected) {
    let type_selector = document.getElementById("explanation")

    if (selected.value === "Bearbeiter") {
        type_selector.textContent = "Als Bearbeiter kann man neue Sitzungen und Benutzer erstellen/bearbeiten."
    }
    else if (selected.value === "Nutzer + Bearbeiten") {
        type_selector.textContent = "Man kann das gleiche wie ein Bearbeiter machen außer Benutzer erstellen."
    }
    else {
        type_selector.textContent = "Als Nutzer kann man die Anwesenheitslisten und etc. sehen."
    }
}