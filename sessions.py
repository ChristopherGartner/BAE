import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

# Force validation disables login validation for sessions
force_validation = True


class Sessions:

    def __init__(self, db):
        self.db = db
        self.VALID_UNTIL_HOURS = 1
        self._sessions = list()
        self.ROLES = {'SYSADMIN': 1000, 'CEO': 100, 'EMPLOYEE': 10}
        self.ALL_PROJECTS_THRESHOLD = 99  # above this all roles can see all projects

    def validate(self, token, role=None, role_required=None, project=None):
        if force_validation:
            return True

        for s in self._sessions:
            if s.token == token:
                if s.valid_until > datetime.now():
                    if role in self.ROLES and role_required in self.ROLES:  # No role assumes no role permissions needed
                        if self.ROLES[role] >= self.ROLES[role_required]:
                            if project is None or self.ROLES[role] > self.ALL_PROJECTS_THRESHOLD:
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
        projects = []
        role = "TEST"
        token = str(uuid.uuid4())
        issued_on = datetime.now()
        valid_until = issued_on + timedelta(hours=self.VALID_UNTIL_HOURS)
        self._sessions.append(Session(token, user, role, projects, issued_on, valid_until))
        return token

    def invalidate_token(self, token):
        for s in self._sessions:
            if s.token == token:
                self._sessions.remove(s)

    def invalidate_user(self, user):
        for s in self._sessions:
            if s.user == user:
                self._sessions.remove(s)


@dataclass
class Session:
    token: str
    user: str
    role: str
    projects: []
    issued_on: datetime
    valid_until: datetime
