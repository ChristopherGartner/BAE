

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


