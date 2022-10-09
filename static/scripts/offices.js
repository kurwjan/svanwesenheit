function change_office_explanation(option) {
    let presence = document.getElementById("presence");
    let tasks = document.getElementById("tasks");

    presence.innerHTML = "<b>Anwesenheitspflicht:</b> " + option.dataset.presence;
    tasks.innerHTML = "<b>Aufgaben:</b> " + option.dataset.tasks;
}