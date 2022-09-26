function show(id) {
    document.getElementById(id).style.display = "block";
}
function hide(id) {
    document.getElementById(id).style.display = "none";
}

function add_person(table, textbox, type) {
    let tbody = document.getElementById(table).getElementsByTagName('tbody')[0];

    let newRow = tbody.insertRow();

    let newCell = newRow.insertCell();

    let newName = document.getElementById(textbox).value;

    newCell.outerHTML = `<td>${newName}</td><input form='today_form' type='hidden' name=${type} value='${newName}'>`

    document.getElementById(textbox).value = "";

}