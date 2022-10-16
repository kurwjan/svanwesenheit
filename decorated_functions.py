from flask import Flask, session, redirect
from flask_mysqldb import MySQL
from functools import wraps

from helpers import get_type

app = Flask(__name__)

# Create database
db = MySQL(app)


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        else:
            cur = db.connection.cursor()

            # Select something in users table from current user_id
            cur.execute('SELECT username FROM users WHERE id = %s AND deleted = 0', [session.get("user_id")])
            check = cur.fetchone()

            # If account is deleted or so, redirect to log in
            if not check:
                session.clear()
                return redirect("/login")

        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """
    Decorate routes to require admin type account.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if get_type(session.get("user_id")) != "Admin":
            return redirect("/")
        return f(*args, **kwargs)

    return decorated_function


def edit_permissions_required(f):
    """
    Decorate routes to require edit permissions.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if get_type(session.get("user_id")) == "Admin" or get_type(session.get("user_id")) == "Bearbeiter":
            return f(*args, **kwargs)
        return redirect("/")

    return decorated_function