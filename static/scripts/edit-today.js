function show(id) {
    document.getElementById(id).style.display = "block";
}
function hide(id) {
    document.getElementById(id).style.display = "none";
}

function add_person(table_id, name, name_id) {
    let tbody = document.getElementById(table_id).getElementsByTagName('tbody')[0];

    let newRow = tbody.insertRow();

    let newCell = newRow.insertCell();

    let newName = document.getElementById(name).value;

    newCell.outerHTML = `<td>${newName}</td><input form='today_form' type='hidden' name=${name_id} value='${newName}'>`
}