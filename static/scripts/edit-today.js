function show(id) {
    document.getElementById(id).style.display = "block";
}
function hide(id) {
    document.getElementById(id).style.display = "none";
}

function add_person(table, textbox, type) {
    let newName = document.getElementById(textbox).value;
    if (newName === "") {
        return;
    }

    let tbody = document.getElementById(table).getElementsByTagName('tbody')[0];

    let newRow = tbody.insertRow();

    newRow.id = newName + "-" + type;

    let newCell = newRow.insertCell();

    let removeCell = newRow.insertCell();

    newCell.outerHTML = `<td style="vertical-align: middle;">${newName}</td><input form='today_form' type='hidden' name=${type} value='${newName}'>`

    removeCell.outerHTML = `<td style="text-align: end;"><button type="button" class="btn btn-outline-danger" onclick="remove_person('${newName + "-" + type}')"><i class="fa-solid fa-xmark"></i></button></td>`

    document.getElementById(textbox).value = "";
}

function remove_person(id) {
    let row = document.getElementById(id);
    row.parentNode.removeChild(row);
}