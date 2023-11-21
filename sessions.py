import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

# Force validation disables login validation for sessions
force_validation = False


class Sessions:

    def __init__(self, db):
        self.db = db
        self.VALID_UNTIL_HOURS = 1
        self._sessions = list()
        self.ROLES = {'SYSADMIN': 1000, 'CEO': 100, 'EMPLOYEE': 10} #TODO fetch this from DB
        self.ALL_PROJECTS_THRESHOLD = 99  # above this all roles can see all projects

    def validate(self, token, role_required=None, project=None):
        if force_validation:
            return True

        for s in self._sessions:
            if s.token == token:
                if s.valid_until > datetime.now():
                    if s.role in self.ROLES and role_required in self.ROLES:  # No role assumes no role permissions needed
                        if self.ROLES[s.role] >= self.ROLES[role_required]:
                            if project is None or self.ROLES[s.role] > self.ALL_PROJECTS_THRESHOLD:
                                # no project given or above threshold allows request
                                return True
                            else:
                                return int(project) in s.projects
                        else:
                            return False
                    else:
                        return True
                else:
                    self._sessions.remove(s)
                    return False

    def register(self, user, password):
        # TODO check PW in DB or against cached list, get role and get allowed projects, if pw wrong return None

        res = self.db.execute("SELECT employee.idemployee, name FROM employee INNER JOIN role ON employee.idrole = role.roleId WHERE Username = %s AND password = %s;", (user, password))
        if len(res) == 0:
            return None
        data = [list(d) for d in res]
        role = data[0][1]
        userid = data[0][0]
        res = self.db.execute("SELECT idproject FROM projectEmployee WHERE projectEmployee.idemployee = %s;", (data[0][0], ))
        data = [list(d) for d in res]
        projects = []
        for r in data:
            projects.append(r[0])
        token = str(uuid.uuid4())
        issued_on = datetime.now()
        valid_until = issued_on + timedelta(hours=self.VALID_UNTIL_HOURS)
        self._sessions.append(Session(userid, token, user, role, projects, issued_on, valid_until))
        return token

    def invalidate_token(self, token):
        for s in self._sessions:
            if s.token == token:
                self._sessions.remove(s)

    def get_user_id(self, token):
        for s in self._sessions:
            if s.token == token:
                return s.userId

    def invalidate_user(self, user):
        for s in self._sessions:
            if s.user == user:
                self._sessions.remove(s)


@dataclass
class Session:
    userId: str
    token: str
    user: str
    role: str
    projects: []
    issued_on: datetime
    valid_until: datetime
