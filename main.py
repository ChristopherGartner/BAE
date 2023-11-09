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
        @self.app.route('/dashboard', methods=['GET'])
        def dashboard():
            if not self.sessions.validate(request.cookies.get('token', default='')):
                return redirect("/login")
            return render_template("dashboard.html")

        @self.app.route('/main_page', methods=['GET'])
        def mainPage():
            if not self.sessions.validate(request.cookies.get('token', default='')):
                return redirect("/login")
            return render_template("mainPage.html")

        @self.app.route('/create_user', methods=['GET'])
        def createUser():
            if not self.sessions.validate(request.cookies.get('token', default='')):
                return redirect("/login")
            return render_template("createUserPage.html")

        @self.app.route('/project/<project_id>')
        def project(project_id):
            if not self.sessions.validate(request.cookies.get('token', default=''), role_required="EMPLOYEE", project=project_id):
                return redirect("/login")

            #TODO get corresponding project data and prepare response
            return make_response()

        # API

        @self.app.route('/api/v1/login', methods=['POST'])
        def api_login():
            username = request.form['username']
            password = request.form['password']

            print(f"Received username: {username}, password: {password}")
            token = self.sessions.validate(username, password)
            if token is None:
                return jsonify({"error": "username & password combination invalid"}), 401
            # on success
            return redirect("/dashboard")


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
            self.app.run(host='0.0.0.0', port=5000)
        else:
            return self.app


if __name__ == '__main__':
    b = BAE()
    b.create_app()
