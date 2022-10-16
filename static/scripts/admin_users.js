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

function change_login_name(display_name) {
    let login_name_textbox = document.getElementById("login_name_textbox");

    login_name_textbox.value = display_name.value.toLowerCase().replace(/\s+/g, ".");
}