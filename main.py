import random
import string
import time
import argparse
import logging
import os

from loguru import logger
from flask import Flask, jsonify, request, render_template, make_response, url_for, send_from_directory
from os.path import dirname, abspath

from werkzeug.utils import redirect

from db import MySQLPool
from sessions import Sessions

force_mobile = False

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
logger.add("latest.log")


def read_args():
    parser = argparse.ArgumentParser(
        description='BAE Project')
    parser.add_argument('dbhost')
    parser.add_argument('dbschema')
    parser.add_argument('dbuser')
    parser.add_argument('dbpw')
    args = vars(parser.parse_args())
    return args

class BAE:

    @logger.catch
    def __init__(self, dbhost=None, dbuser=None, dbpw=None, dbschema=None):
        logger.info("Starting up...")

        args = read_args()
        if not dbhost is None:
            args['dbhost'] = dbhost
            args['dbuser'] = dbuser
            args['dbpw'] = dbpw
            args['dbschema'] = dbschema
        self.db = MySQLPool(host=args['dbhost'], user=args['dbuser'], password=args['dbpw'], database=args['dbschema'],
                            pool_size=15)
        self.sessions = Sessions(self.db)

    def createHash(self, k):
        return ''.join(random.choices(string.ascii_letters + string.digits, k))

    def __log(self, req):
        ip = ""
        if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
            ip = (request.environ['REMOTE_ADDR'])
        else:
            ip = (request.environ['HTTP_X_FORWARDED_FOR'])  # if behind a proxy
        logger.info(ip + " " + req.environ.get('REQUEST_URI'))
        self.db.execute("INSERT INTO hits(ip, timestamp, url, sec_ch_ua, sec_ch_ua_mobile, sec_ch_ua_platform, "
                        "user_agent, accept_language, path, query) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);",
                        (ip, int(time.time()), req.environ.get('REQUEST_URI'), req.environ.get('HTTP_SEC_CH_UA'),
                         req.environ.get('HTTP_SEC_CH_UA_MOBILE'), req.environ.get('HTTP_SEC_CH_UA_PLATFORM'),
                         req.environ.get('HTTP_USER_AGENT'), req.environ.get('HTTP_ACCEPT_LANGUAGE'),
                         req.environ.get('PATH_INFO'), req.environ.get('QUERY_STRING')), commit=True)
        return ip

    def isMobile(self, request):
        ua = request.headers.get('User-Agent')
        if ua is None:
            ua = ""
        ua = ua.lower()
        if force_mobile:
            ua += "android"
        return "iphone" in ua or "android" in ua

    @logger.catch
    def create_app(self):

        self.app = Flask(__name__)

        @self.app.before_request
        def before():
            self.__log(request)

        @self.app.route('/', methods=['GET', 'POST'])
        def index():
            return render_template("index.html")

        @self.app.route('/login', methods=['GET'])
        def login():
            return render_template("login.html")

        # Protected routes
        @self.app.route('/main_page', methods=['GET'])
        def mainPage():
            token = request.cookies.get('token', default='')
            if not self.sessions.validate(token):
                return redirect("/login")
            user_id = self.sessions.get_user_id(token)
            return render_template("mainPage.html", user_permission_level=self.sessions.get_user_permission_level(token), user_id=str(user_id))

        @self.app.route('/create_user', methods=['GET'])
        def createUser():
            if not self.sessions.validate(request.cookies.get('token', default='')):
                return redirect("/login")
            return render_template("createUserPage.html")

        @self.app.route('/create_customer', methods=['GET'])
        def createCustomer():
            if not self.sessions.validate(request.cookies.get('token', default='')):
                return redirect("/login")
            return render_template("createCustomer.html")

        @self.app.route('/create_project', methods=['GET'])
        def createProject():
            if not self.sessions.validate(request.cookies.get('token', default='')):
                return redirect("/login")
            return render_template("createProject.html")

        @self.app.route('/project/<project_id>')
        def project(project_id):
            if not self.sessions.validate(request.cookies.get('token', default=''), role_required="EMPLOYEE",
                                          project=project_id):
                return redirect("/login")

            # TODO get corresponding project data and prepare response
            return render_template("project.html")

        # API

        @self.app.route('/api/v1/login', methods=['POST'])
        def api_login():
            username = request.form['username']
            password = request.form['password']

            token = self.sessions.register(username, password)
            if token is None:
                return jsonify({"error": "username & password combination invalid"}), 401
            # on success
            resp = make_response(jsonify({"success": "Login successful"}), 200)
            resp.set_cookie("token", token)
            return resp

        @self.app.route('/api/v1/project_list', methods=['GET'])
        def api_load_project_data():
            userId = self.sessions.get_user_id(request.cookies.get("token", default="NOT FOUND"))

            selectedProjects = self.db.execute(""
                            f"SELECT project.idproject, customer.name, project.startDate, project.plannedEndingDate, project.budget, project.priority FROM project INNER JOIN projectEmployee ON project.idProject = projectEmployee.idProject INNER JOIN customer ON project.idcustomer = customer.idcustomer "
                            f"WHERE projectEmployee.idemployee = {userId};"
                            )

            return jsonify(selectedProjects)

        @self.app.route('/api/v1/project_list_total', methods=['GET'])
        def api_load_all_project_data():
            userId = self.sessions.get_user_id(request.cookies.get("token", default="NOT FOUND"))

            selectedProjects = self.db.execute(""
                            f"SELECT project.idproject, customer.name, project.startDate, project.plannedEndingDate, project.budget, project.priority FROM project INNER JOIN customer ON project.idcustomer = customer.idcustomer;"
                            )

            return jsonify(selectedProjects)

        @self.app.route('/api/v1/customer_list_id_and_name', methods=['GET'])
        def api_load_customer_id_and_name():
            selectedCustomers = self.db.execute(f"SELECT customer.idcustomer, customer.name FROM customer")
            return jsonify(selectedCustomers)

        @self.app.route('/api/v1/customer_list', methods=['GET'])
        def api_load_customers():
            selectedCustomers = self.db.execute(
                f"SELECT customer.idcustomer, customer.name, Address.streetName, Address.houseNumber, city.postCode, city.cityName, city.state, city.country FROM customer INNER JOIN Address ON customer.idaddress = Address.idAddress INNER JOIN city ON Address.idcity = city.idcity"
            )
            return jsonify(selectedCustomers)

        @self.app.route('/api/v1/employees_list', methods=['GET'])
        def api_load_employees():
            selectedEmployees = self.db.execute(
                f"SELECT employee.idemployee, employee.firstName, employee.lastName, employee.gender, employee.position, employee.saleryPerHour, employee.titel, employee.birthDate, employee.informations, Address.streetName, Address.houseNumber, city.postCode, city.cityName, city.state, city.country, employee.Username, role.nicename FROM employee INNER JOIN Address ON employee.idaddress = Address.idAddress INNER JOIN city ON Address.idcity = city.idcity INNER JOIN role ON employee.idrole = role.roleid"
            )
            return jsonify(selectedEmployees)

        @self.app.route('/api/v1/user_main_page_data', methods=['GET'])
        def api_load_user_main_page_data():
            userFullName = self.sessions.get_user_full_name_with_salutation(request.cookies.get("token", default="NOT FOUND"))
            userTitel = self.sessions.get_user_job_titel(request.cookies.get("token", default="NOT FOUND"))
            userId = self.sessions.get_user_id(request.cookies.get("token", default="NOT FOUND"))

            return jsonify({
                "userFullName": userFullName,
                "userTitel": userTitel,
                "userId": userId
            })

        @self.app.route('/api/v1/edit_project_data/<project_id>')
        def api_edit_project_data(project_id):
            res = self.db.execute("SELECT project.idproject, project.idcustomer, customer.name, project.startDate, project.plannedEndingDate, project.budget, project.priority FROM project INNER JOIN customer ON project.idcustomer = customer.idcustomer WHERE idproject=%s;", (project_id,))
            return jsonify(res[0])

        @self.app.route('/api/v1/edit_customer_data/<customer_id>')
        def api_edit_customer_data(customer_id):
            res = self.db.execute(
                "SELECT customer.idcustomer, customer.name, Address.streetName, Address.houseNumber, city.cityName, city.postCode, city.country, city.state FROM customer INNER JOIN Address ON customer.idaddress = Address.idaddress INNER JOIN city ON Address.idcity = city.idcity WHERE customer.idcustomer=%s;",
                (customer_id,))
            return jsonify(res[0])

        @self.app.route('/api/v1/edit_user_data/<user_id>')
        def api_edit_user_data(user_id):
            res = self.db.execute(
                "SELECT Address.streetName, Address.houseNumber, city.cityName, city.postCode, city.country, city.state, employee.titel, employee.position, employee.gender, employee.birthDate, employee.firstName, employee.lastName, employee.saleryPerHour, employee.idrole, employee.Username, employee.password, employee.informations FROM employee INNER JOIN Address ON employee.idaddress = Address.idaddress INNER JOIN city ON Address.idcity = city.idcity WHERE employee.idemployee=%s;",
                (user_id,))
            return jsonify(res[0])

        @self.app.route('/api/v1/project_data/<project_id>')
        def api_project_data(project_id):
            res = self.db.execute("SELECT * FROM project INNER JOIN customer ON project.idcustomer = customer.idcustomer WHERE idproject=%s;", (project_id, ))
            result = {"project_data": res[0]}
            users = self.db.execute("SELECT * FROM employee INNER JOIN projectEmployee ON employee.idemployee = projectEmployee.idemployee WHERE idproject = %s;", (project_id, ))
            result["users"] = users
            return jsonify(result)


        @self.app.route('/api/v1/all_users', methods=['GET'])
        def api_all_users():
            return jsonify(self.db.execute("SELECT * FROM BAE.employee;"))


        @self.app.route('/api/v1/project_add_user', methods=['POST'])
        def api_project_add_user():
            print(request.json)
            self.db.execute("INSERT INTO projectEmployee VALUES(%s, %s, false);",
                            (request.json["user_id"], request.json["project_id"],), commit=True)
            return jsonify({"status": 200})


        @self.app.route('/api/v1/project_remove_user', methods=['POST'])
        def api_project_remove_user():
            print(request.json)
            self.db.execute("DELETE FROM projectEmployee WHERE idemployee = %s AND idproject = %s;",
                            (request.json["user_id"], request.json["project_id"],), commit=True)
            return jsonify({"status": 200})


        @self.app.route('/api/v1/create_user', methods=['POST'])
        def api_create_user():
            input_street = request.form['input_street']
            input_house_number = request.form['input_house_number']
            input_city = request.form['input_city']
            input_PLZ = request.form['input_PLZ']
            input_country = request.form['input_country']
            input_state = request.form['input_state']
            input_title = request.form['input_title']
            input_job_position = request.form['input_job_position']
            input_gender = request.form['input_gender']
            input_birth_date = request.form['input_birth_date']
            input_first_name = request.form['input_first_name']
            input_last_name = request.form['input_last_name']
            input_salery_per_hour = request.form['input_salery_per_hour']
            input_role = request.form['input_role']
            input_informations = request.form['input_informations']
            input_password = request.form['input_password']
            input_username = request.form['input_username']

            error_text = None
            error_occurred = False

            if input_street == "":
                error_text = "Das Straßenfeld wurde nicht ausgefüllt!"
            elif input_house_number == "":
                error_text = "Das Hausnummerfeld wurde nicht ausgefüllt!"
            elif input_city == "":
                error_text = "Das Stadtfeld wurde nicht ausgefüllt!"
            elif input_PLZ == "":
                error_text = "Das PLZ-Feld wurde nicht ausgefüllt!"
            elif input_country == "":
                error_text = "Das Landfeld wurde nicht ausgefüllt!"
            elif input_state == "":
                error_text = "Das Bundesland-/Staatfeld wurde nicht ausgefüllt!"
            elif input_job_position == "":
                error_text = "Das Job-Positionsfeld wurde nicht ausgefüllt!"
            elif input_gender == "":
                error_text = "Das Geschlechtsfeld wurde nicht ausgefüllt!"
            elif input_birth_date == "":
                error_text = "Das Geburtsdatumsfeld wurde nicht ausgefüllt!"
            elif input_first_name == "":
                error_text = "Das Vornamenfeld wurde nicht ausgefüllt!"
            elif input_last_name == "":
                error_text = "Das Nachnamenfeld wurde nicht ausgefüllt!"
            elif input_salery_per_hour == "":
                error_text = "Das Bezahlung-Pro-Stundefeld wurde nicht ausgefüllt!"
            elif input_role == "":
                error_text = "Das Rollenfeld wurde nicht ausgefüllt!"
            elif input_username == "":
                error_text = "Das Nutzernamenfeld wurde nicht ausgefüllt!"
            elif input_password == "":
                error_text = "Das Passwortfeld wurde nicht ausgefüllt!"

            if (error_text is not None):
                error_occurred = True

            if not error_occurred:
                try:
                    val = float(input_salery_per_hour)
                except ValueError:
                    error_text = "'" + input_salery_per_hour + "' ist kein numerischer Wert! Bitte gebe im 'Bezahlung-pro-Stundefeld' einen numerischen Wert an!"
                    error_occurred = True

            if error_occurred:
                return redirect("/create_user?error=1&error_message=" + error_text)

            # Handle database management insertion or reading for address
            cityDatabaseEntry = self.db.execute(f"SELECT * FROM city WHERE city.postcode = {input_PLZ};")
            cityExists = len(cityDatabaseEntry) != 0

            if not cityExists:
                self.db.execute(f"INSERT INTO city(country, postCode, state, cityName) VALUES ('{input_country}', {input_PLZ}, '{input_state}', '{input_city}');", commit=True)

            cityIdSelectResult = self.db.execute(f"SELECT city.idcity FROM city WHERE city.postCode = {input_PLZ};")
            cityId = cityIdSelectResult[0][0]

            self.db.execute(f"INSERT INTO Address(houseNumber, streetName, idcity) VALUES ({input_house_number}, '{input_street}', {cityId});", commit=True)
            addressIdSelectResult = self.db.execute(f"SELECT Address.idAddress FROM Address WHERE Address.houseNumber = {input_house_number} AND Address.streetName = '{input_street}' AND Address.idcity = {cityId};")
            addressId = addressIdSelectResult[0][0]

            self.db.execute(
                "INSERT INTO employee(firstName, lastName, gender, position, saleryPerHour, titel, birthDate, informations, idaddress, password, Username, idrole) VALUES "
                + "('" + input_first_name + "','" + input_last_name + "','" + input_gender + "','" + input_job_position + "'," + input_salery_per_hour + ",'" + input_title + "','" + input_birth_date + "','" + input_informations + f"<',{addressId},'" + input_password + "','" + input_username + "', 3);",
                commit=True)

            return redirect("/create_user")

        @self.app.route('/api/v1/update_user/<user_id>', methods=['POST'])
        def api_update_user(user_id):
            input_street = request.form['input_street']
            input_house_number = request.form['input_house_number']
            input_city = request.form['input_city']
            input_plz = request.form['input_PLZ']
            input_country = request.form['input_country']
            input_state = request.form['input_state']
            input_title = request.form['input_title']
            input_job_position = request.form['input_job_position']
            input_gender = request.form['input_gender']
            input_birth_date = request.form['input_birth_date']
            input_first_name = request.form['input_first_name']
            input_last_name = request.form['input_last_name']
            input_salery_per_hour = request.form['input_salery_per_hour']
            input_role = request.form['input_role']
            input_informations = request.form['input_informations']
            input_password = request.form['input_password']
            input_username = request.form['input_username']

            addressId = \
            self.db.execute(f"SELECT employee.idaddress FROM employee WHERE employee.idemployee = {user_id};")[0][0]
            cityId = self.db.execute(f"SELECT Address.idcity FROM Address WHERE Address.idAddress = {addressId};")[0][0]

            self.db.execute(
                f"UPDATE employee SET employee.titel = '{input_title}', employee.position = '{input_job_position}', employee.gender = '{input_gender}', employee.birthDate = '{input_birth_date}', employee.firstName = '{input_first_name}', employee.lastName = '{input_last_name}', employee.saleryPerHour = {input_salery_per_hour}, employee.idrole = {input_role}, employee.informations = '{input_informations}', employee.password = '{input_password}', employee.Username = '{input_username}' WHERE employee.idemployee = {user_id};",
                commit=True)
            self.db.execute(
                f"UPDATE Address SET Address.houseNumber = {input_house_number}, Address.streetName = '{input_street}' WHERE Address.idaddress = {addressId};",
                commit=True)
            self.db.execute(
                f"UPDATE city SET city.country = '{input_country}', city.postCode = '{input_plz}', city.state = '{input_state}', city.cityName = '{input_city}' WHERE city.idcity = {cityId};",
                commit=True)

            return redirect("/create_user?edit=1&id=" + user_id)

        @self.app.route('/api/v1/create_project', methods=['POST'])
        def api_create_project():
            input_project_begin = request.form['input_project_begin']
            input_project_end = request.form['input_project_end']
            input_budget = request.form['input_budget']
            input_priority = request.form['input_priority']
            input_customer_id = request.form['input_customer_id']

            error_text = None
            error_occurred = False

            user_id = self.sessions.get_user_id(request.cookies.get("token", default="NOT FOUND"))

            if input_customer_id == "":
                error_text = "Das Kunden-ID-Feld wurde nicht befüllt!"
            elif input_project_begin == "":
                error_text = "Das Projektbeginnfeld wurde nicht ausgefüllt!"
            elif input_project_end == "":
                error_text = "Das voraussichtliches Projektendefeld wurde nicht ausgefüllt!"
            elif input_budget == "":
                error_text = "Das Budgetfeld wurde nicht ausgefüllt!"
            elif input_priority == "":
                error_text = "Das Projektprioritätfeld wurde nicht ausgefüllt!"
            elif input_customer_id == "":
                error_text = "Das Kunden-ID-Feld wurde nicht befüllt!"

            if (error_text is not None):
                error_occurred = True

            if error_occurred:
                return redirect("/create_project?error=1&error_message=" + error_text)

            self.db.execute(
                "INSERT INTO project(idcustomer, startDate, plannedEndingDate, idaddress, priority, budget) VALUES "
                + "(" + input_customer_id + ", '" + input_project_begin + "','" + input_project_end + "',3,'" + input_priority + "'," + input_budget + ");",
                commit=True)
            res = self.db.execute(
                "SELECT idproject FROM project WHERE idcustomer = %s AND startDate = %s AND plannedEndingDate = %s AND idaddress = %s AND priority = %s AND budget = %s;", (input_customer_id, input_project_begin, input_project_end, 3, input_priority, input_budget, )
            )
            self.db.execute(
                "INSERT INTO projectEmployee VALUES(%s, %s, %s);", (user_id, res[0][0], 1,), commit=True
            )
            return redirect("/create_project")

        @self.app.route('/api/v1/update_project/<project_id>', methods=['POST'])
        def api_update_project(project_id):
            input_project_begin = request.form['input_project_begin']
            input_project_end = request.form['input_project_end']
            input_budget = request.form['input_budget']
            input_priority = request.form['input_priority']
            input_customer_id = request.form['input_customer_id']

            self.db.execute(f"UPDATE project SET project.idcustomer = {input_customer_id}, project.startDate = '{input_project_begin}', project.plannedEndingDate = '{input_project_end}', project.budget = {input_budget}, project.priority = {input_priority} WHERE project.idproject = {project_id};", commit=True)

            return redirect("/create_project?edit=1&id=" + project_id)

        @self.app.route('/api/v1/create_customer', methods=['POST'])
        def api_create_customer():
            input_name = request.form['input_name']
            input_street = request.form['input_street']
            input_house_number = request.form['input_house_number']
            input_city = request.form['input_city']
            input_plz = request.form['input_plz']
            input_country = request.form['input_country']
            input_state = request.form['input_state']

            error_text = None
            error_occurred = False

            if input_name == "":
                error_text = "Das Namensfeld wurde nicht ausgefüllt!"
            elif input_street == "":
                error_text = "Das Straßenfeld wurde nicht ausgefüllt!"
            elif input_house_number == "":
                error_text = "Das Hausnummer wurde nicht ausgefüllt!"
            elif input_city == "":
                error_text = "Das Stadtfeld wurde nicht ausgefüllt!"
            elif input_plz == "":
                error_text = "Das PLZ-Feld wurde nicht ausgefüllt!"
            elif input_country == "":
                error_text = "Das Landfeld wurde nicht ausgefüllt!"
            elif input_state == "":
                error_text = "Das Staat-/Bundeslandfeld wurde nicht ausgefüllt!"

            if error_text is not None:
                error_occurred = True

            if error_occurred:
                return redirect("/create_customer?error=1&error_message=" + error_text)

            # Handle database management insertion or reading for address
            cityDatabaseEntry = self.db.execute(f"SELECT * FROM city WHERE city.postcode = {input_plz};")
            cityExists = len(cityDatabaseEntry) != 0

            if not cityExists:
                self.db.execute(
                    f"INSERT INTO city(country, postCode, state, cityName) VALUES ('{input_country}', {input_plz}, '{input_state}', '{input_city}');",
                    commit=True)

            cityIdSelectResult = self.db.execute(f"SELECT city.idcity FROM city WHERE city.postCode = {input_plz};")
            cityId = cityIdSelectResult[0][0]

            self.db.execute(
                f"INSERT INTO Address(houseNumber, streetName, idcity) VALUES ({input_house_number}, '{input_street}', {cityId});",
                commit=True)
            addressIdSelectResult = self.db.execute(
                f"SELECT Address.idAddress FROM Address WHERE Address.houseNumber = {input_house_number} AND Address.streetName = '{input_street}' AND Address.idcity = {cityId};")
            addressId = addressIdSelectResult[0][0]

            self.db.execute(
                "INSERT INTO customer(idaddress, name) VALUES "
                + f"({addressId}, '" + input_name + "');",
                commit=True)

            return redirect("/create_customer")

        @self.app.route('/api/v1/update_customer/<customer_id>', methods=['POST'])
        def api_update_customer(customer_id):
            input_name = request.form['input_name']
            input_street = request.form['input_street']
            input_house_number = request.form['input_house_number']
            input_city = request.form['input_city']
            input_plz = request.form['input_plz']
            input_country = request.form['input_country']
            input_state = request.form['input_state']

            addressId = self.db.execute(f"SELECT customer.idaddress FROM customer WHERE customer.idcustomer = {customer_id};")[0][0]
            cityId = self.db.execute(f"SELECT Address.idcity FROM Address WHERE Address.idAddress = {addressId};")[0][0]

            self.db.execute(f"UPDATE customer SET customer.name = '{input_name}' WHERE customer.idcustomer = {customer_id};", commit=True)
            self.db.execute(f"UPDATE Address SET Address.houseNumber = {input_house_number}, Address.streetName = '{input_street}' WHERE Address.idaddress = {addressId};", commit=True)
            self.db.execute(f"UPDATE city SET city.country = '{input_country}', city.postCode = '{input_plz}', city.state = '{input_state}', city.cityName = '{input_city}' WHERE city.idcity = {cityId};", commit=True)

            return redirect("/create_customer?edit=1&id=" + customer_id)

        @self.app.route('/android-chrome-192x192.png')
        @self.app.route('/android-chrome-512x512.png')
        @self.app.route('/apple-touch-icon.png')
        @self.app.route('/favicon.ico')
        @self.app.route('/favicon-16x16.png')
        @self.app.route('/favicon-32x32.png')
        def static_from_ico():
            return send_from_directory(os.path.join(self.app.static_folder, 'ico'), request.path[1:])

        @self.app.route('/robots.txt')
        @self.app.route('/sitemap.xml')
        def static_from_root():
            return send_from_directory(self.app.static_folder, request.path[1:])

        if __name__ == '__main__':
            self.app.run(host='0.0.0.0', port=17500)
        else:
            return self.app


if __name__ == '__main__':
    b = BAE()
    b.create_app()
