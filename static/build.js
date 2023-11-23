var proj_id = 0;

function setup_login_form(){
    console.log("preparing login")

    document.getElementById("username").addEventListener("input", (event) => {document.getElementById("login_error").classList.add("hidden")});
        document.getElementById("password").addEventListener("input", (event) => {document.getElementById("login_error").classList.add("hidden")});

    $('#loginForm')
        .ajaxForm({
            url : 'api/v1/login',
            method: 'POST',
            dataType : 'json',
            success : function (data) {
                window.location.href = "/main_page"
            },
            error : function (data) {
                document.getElementById("login_error").classList.remove("hidden")
            }
        })
    ;
}

function build_project_page() {
    console.log("Building project page...")
    tmp = window.location.pathname.split("/")
    proj_id = tmp[tmp.length - 1]


    fetch('/api/v1/project_data/' + proj_id, {
        method: 'GET',
        headers: {'Content-Type': 'application/json'}
    }).then(res => res.json()).then(jsonRes => {
        console.log(jsonRes)
        pd = jsonRes["project_data"]
        us = jsonRes["users"]

        document.getElementById("project_title").innerText = "Projekt " + pd[0]
        document.getElementById("customer").innerText = pd[9]
        document.getElementById("date_start").innerText = pd[2]
        document.getElementById("date_end").innerText = pd[3]
        document.getElementById("priority").innerText = pd[5]
        document.getElementById("budget").innerText = pd[6]


        $.each(us, function(){
            if(this[15] == 1){
               document.getElementById("created_by").innerText = this[1] + " " + this[2]
               var op = document.createElement("option")
               op.value = this[0]
               op.innerText = this[2] + ", " + this[1] + " (Ersteller)"
               op.disabled = true;
               op.style = "background-color: lightgrey;"
               document.getElementById("users_remove").appendChild(op);
            } else {
               var op = document.createElement("option")
               op.value = this[0]
               op.innerText = this[2] + ", " + this[1]
               document.getElementById("users_remove").appendChild(op);
            }
        })

        fetch('/api/v1/all_users', {
            method: 'GET',
            headers: {'Content-Type': 'application/json'}
        }).then(res => res.json()).then(resp => {
            $.each(resp, function() {
                var u1 = this
                var isContained = false
                $.each(us, function() {
                    if(u1[0] == this[0]){
                        isContained = true
                    }
                })
                if(!isContained){
                   var op = document.createElement("option")
                   op.value = this[0]
                   op.innerText = this[2] + ", " + this[1]
                   document.getElementById("users_add").appendChild(op);
                }
            })
        })
    })
}


function remove_user() {
    var val = document.getElementById("users_remove").value
    console.log(val)
    if(val === ""){
        return
    }

    (async () => {
      const rawResponse = await fetch('/api/v1/project_remove_user', {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({"project_id": proj_id, "user_id": val})
      });
      const content = await rawResponse.json();

      console.log(content);
      location.reload();
    })();

}

function add_user() {
    var val = document.getElementById("users_add").value
    console.log(val)
    if(val === ""){
        return
    }

    (async () => {
      const rawResponse = await fetch('/api/v1/project_add_user', {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({"project_id": proj_id, "user_id": val})
      });
      const content = await rawResponse.json();

      console.log(content);
      location.reload();
    })();
}


function fillProjectTable()
{
    document.getElementById("table_headline").innerText = "Individuelle Projektübersicht"

    fetch('/api/v1/project_list', {
    method: 'GET',
    headers: {'Content-Type': 'application/json'}
}).then(res => res.json()).then(jsonRes => {
    let new_thread = document.createElement('tbody');

    let new_tbody = document.createElement('tbody');
    new_tbody.setAttribute("id", "project_table_body");

    let element_tablerow = document.createElement("tr")

    let element_projectId = document.createElement("th")
    let element_customer = document.createElement("th")
    let element_startDate = document.createElement("th")
    let element_endingDate = document.createElement("th")
    let element_budget = document.createElement("th")
    let element_priority = document.createElement("th")

    element_projectId.innerText = "Projekt-ID"
    element_customer.innerText = "Kunde"
    element_startDate.innerText = "Startdatum"
    element_endingDate.innerText = "Enddatum"
    element_budget.innerText = "Budget"
    element_priority.innerText = "Priorität"

    element_tablerow.appendChild(element_projectId)
    element_tablerow.appendChild(element_customer)
    element_tablerow.appendChild(element_startDate)
    element_tablerow.appendChild(element_endingDate)
    element_tablerow.appendChild(element_budget)
    element_tablerow.appendChild(element_priority)

    new_thread.appendChild(element_tablerow);

    let newTable = document.createElement("table");
    newTable.setAttribute("class", "mitarbeiterbersicht-projekte-textIchHasseMeinLeben styled-table");
    newTable.setAttribute("id", "project_table");

    newTable.appendChild(new_thread);
    newTable.appendChild(new_tbody);

    $.each(jsonRes, function() {
         let temp = this
         let newRow = document.createElement("tr")
         $.each(temp, function(){
             let newCell = document.createElement("td")
             newCell.innerText = this
             newRow.appendChild(newCell)
         })
        let projectId = temp[0];

        let editCell = document.createElement("td");
        let editButton = document.createElement("a");
        editButton.innerText = "Bearbeiten";
        editButton.setAttribute("onclick", "window.location.href='/create_project?edit=1&id=" + projectId + "'")
        editButton.setAttribute("onmousedown", "this.style.backgroundColor='#003100'")
        editButton.setAttribute("onmouseup", "this.style.backgroundColor='#4CAF50'")
        editButton.setAttribute("style", "display: inline-block; padding: 10px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; cursor: pointer;")


        editCell.appendChild(editButton);
        newRow.appendChild(editCell);


        let detailsCell = document.createElement("td");
        let detailsButton = document.createElement("a");
        detailsButton.innerText = "Details";
        detailsButton.setAttribute("onclick", "window.location.href='/project/" + projectId + "'")
        detailsButton.setAttribute("onmousedown", "this.style.backgroundColor='#CCAC4F'")
        detailsButton.setAttribute("onmouseup", "this.style.backgroundColor='#FFD763'")
        detailsButton.setAttribute("style", "display: inline-block; padding: 10px; background-color: #FFD763; color: white; text-decoration: none; border-radius: 5px; cursor: pointer;")


        detailsCell.appendChild(detailsButton);
        newRow.appendChild(detailsCell);

        new_tbody.appendChild(newRow);
    });

    document.getElementById("project_table").parentNode.replaceChild(newTable, document.getElementById("project_table"));
})
}

function fillCustomerTable() {
    document.getElementById("table_headline").innerText = "Kundenübersicht"
    fetch('/api/v1/customer_list', {
        method: 'GET',
        headers: {'Content-Type': 'application/json'}
    }).then(res => res.json()).then(jsonRes => {
        let new_thread = document.createElement('tbody');

        let new_tbody = document.createElement('tbody');
        new_tbody.setAttribute("id", "project_table_body");

        let element_tablerow = document.createElement("tr")

        let element_customerId = document.createElement("th")
        let element_customerName = document.createElement("th")
        let element_streetName = document.createElement("th")
        let element_houseNumber = document.createElement("th")
        let element_cityPostCode = document.createElement("th")
        let element_cityName = document.createElement("th")
        let element_cityState = document.createElement("th")
        let element_cityCountry = document.createElement("th")

        element_customerId.innerText = "Kunden-ID"
        element_customerName.innerText = "Kundenname"
        element_streetName.innerText = "Straßenname"
        element_houseNumber.innerText = "Hausnummer"
        element_cityPostCode.innerText = "PLZ"
        element_cityName.innerText = "Stadt"
        element_cityState.innerText = "Bundesland/Staat"
        element_cityCountry.innerText = "Land"

        element_tablerow.appendChild(element_customerId)
        element_tablerow.appendChild(element_customerName)
        element_tablerow.appendChild(element_streetName)
        element_tablerow.appendChild(element_houseNumber)
        element_tablerow.appendChild(element_cityPostCode)
        element_tablerow.appendChild(element_cityName)
        element_tablerow.appendChild(element_cityState)
        element_tablerow.appendChild(element_cityCountry)

        new_thread.appendChild(element_tablerow);

        let newTable = document.createElement("table");
        newTable.setAttribute("class", "mitarbeiterbersicht-projekte-textIchHasseMeinLeben styled-table");
        newTable.setAttribute("id", "project_table");

        newTable.appendChild(new_thread);
        newTable.appendChild(new_tbody);

        $.each(jsonRes, function () {
            let temp = this
            let newRow = document.createElement("tr")
            $.each(temp, function () {
                let newCell = document.createElement("td")
                newCell.innerText = this
                newRow.appendChild(newCell)
            })
            let customerId = temp[0];

            let editCell = document.createElement("td");
            let editButton = document.createElement("a");
            editButton.innerText = "Bearbeiten";
            editButton.setAttribute("onclick", "window.location.href='{{url_for('createCustomer')}}?edit=1&id=" + customerId + "'")
            editButton.setAttribute("onmousedown", "this.style.backgroundColor='#003100'")
            editButton.setAttribute("onmouseup", "this.style.backgroundColor='#4CAF50'")
            editButton.setAttribute("style", "display: inline-block; padding: 10px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; cursor: pointer;")

            editCell.appendChild(editButton);
            newRow.appendChild(editCell)

            new_tbody.appendChild(newRow)
        });

        document.getElementById("project_table").parentNode.replaceChild(newTable, document.getElementById("project_table"));
    })
}

function fillEmployeeTable() {
    document.getElementById("table_headline").innerText = "Mitarbeiterübersicht"
    fetch('/api/v1/employees_list', {
        method: 'GET',
        headers: {'Content-Type': 'application/json'}
    }).then(res => res.json()).then(jsonRes => {
        let new_thread = document.createElement('tbody');

        let new_tbody = document.createElement('tbody');
        new_tbody.setAttribute("id", "project_table_body");

        let element_tablerow = document.createElement("tr")

        let element_employeeId = document.createElement("th")
        let element_firstName = document.createElement("th")
        let element_lastName = document.createElement("th")
        let element_gender = document.createElement("th")
        let element_position = document.createElement("th")
        let element_saleryPerHour = document.createElement("th")
        let element_titel = document.createElement("th")
        let element_birthDate = document.createElement("th")
        let element_informations = document.createElement("th")
        let element_streetName = document.createElement("th")
        let element_houseNumber = document.createElement("th")
        let element_cityPostCode = document.createElement("th")
        let element_cityName = document.createElement("th")
        let element_state = document.createElement("th")
        let element_country = document.createElement("th")
        let element_username = document.createElement("th")
        let element_role = document.createElement("th")

        element_employeeId.innerText = "Mitarbeiter-ID"
        element_firstName.innerText = "Vorname(n)"
        element_lastName.innerText = "Nachname"
        element_gender.innerText = "Geschlecht"
        element_position.innerText = "Berufsposition"
        element_saleryPerHour.innerText = "Bezahlung/Stunde (in €)"
        element_titel.innerText = "Titel"
        element_birthDate.innerText = "Geburtsdatum"
        element_informations.innerText = "Informationen"
        element_streetName.innerText = "Straßenname"
        element_houseNumber.innerText = "Hausnummer"
        element_cityPostCode.innerText = "PLZ"
        element_cityName.innerText = "Stadt"
        element_state.innerText = "Bundesland/Staat"
        element_country.innerText = "Land"
        element_username.innerText = "Benutzername"
        element_role.innerText = "Rolle"

        element_tablerow.appendChild(element_employeeId)
        element_tablerow.appendChild(element_firstName)
        element_tablerow.appendChild(element_lastName)
        element_tablerow.appendChild(element_gender)
        element_tablerow.appendChild(element_position)
        element_tablerow.appendChild(element_saleryPerHour)
        element_tablerow.appendChild(element_titel)
        element_tablerow.appendChild(element_birthDate)
        element_tablerow.appendChild(element_informations)
        element_tablerow.appendChild(element_streetName)
        element_tablerow.appendChild(element_houseNumber)
        element_tablerow.appendChild(element_cityPostCode)
        element_tablerow.appendChild(element_cityName)
        element_tablerow.appendChild(element_state)
        element_tablerow.appendChild(element_country)
        element_tablerow.appendChild(element_username)
        element_tablerow.appendChild(element_role)

        new_thread.appendChild(element_tablerow);

        let newTable = document.createElement("table");
        newTable.setAttribute("class", "mitarbeiterbersicht-projekte-textIchHasseMeinLeben styled-table");
        newTable.setAttribute("id", "project_table");

        newTable.appendChild(new_thread);
        newTable.appendChild(new_tbody);

        $.each(jsonRes, function () {
            let temp = this
            let newRow = document.createElement("tr")
            $.each(temp, function () {
                let newCell = document.createElement("td")
                newCell.innerText = this
                newRow.appendChild(newCell)
            })
            let employeeId = temp[0];

            let editCell = document.createElement("td");
            let editButton = document.createElement("a");
            editButton.innerText = "Bearbeiten";
            editButton.setAttribute("onclick", "window.location.href='/create_user?edit=1&id=" + employeeId + "'")
            editButton.setAttribute("onmousedown", "this.style.backgroundColor='#003100'")
            editButton.setAttribute("onmouseup", "this.style.backgroundColor='#4CAF50'")
            editButton.setAttribute("style", "display: inline-block; padding: 10px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; cursor: pointer;")

            editCell.appendChild(editButton);
            newRow.appendChild(editCell)

            new_tbody.appendChild(newRow)
        });

        document.getElementById("project_table").parentNode.replaceChild(newTable, document.getElementById("project_table"));
    })
}

function setUserLabels()
{
    fetch('/api/v1/user_main_page_data', {
        method: 'GET',
        headers: {'Content-Type': 'application/json'}
    }).then(res => res.json()).then(dictionary => {
        document.getElementById("label_user_full_name").innerText = dictionary["userFullName"];
        document.getElementById("label_user_position").innerText = dictionary["userTitel"];
        document.getElementById("label_user_id").innerText = "UserID: " + dictionary["userId"];

        document.getElementById("label_user_full_name").style.fontWeight = "bold";
        document.getElementById("label_user_full_name").style.fontSize = "18px";

        document.getElementById("label_user_position").style.fontSize = "14px";

        document.getElementById("label_user_id").style.fontSize = "10px";
    })
}