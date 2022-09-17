from flask import Flask, render_template, session, redirect, request, flash, get_flashed_messages
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash, generate_password_hash
from flask_session import Session
from functools import wraps

app = Flask(__name__)

app.config['MYSQL_USER'] = input("Enter username: ")
app.config['MYSQL_PASSWORD'] = input("Enter password: ")
app.config['MYSQL_DB'] = input("Enter database: ")
app.config['MYSQL_HOST'] = input("Enter host: ")

# Create database
db = MySQL(app)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_type") != "Admin":
            return redirect("/")
        return f(*args, **kwargs)

    return decorated_function


def editor_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_type") == "Admin" or session.get("user_type") == "Bearbeiter":
            return f(*args, **kwargs)
        return redirect("/")

    return decorated_function


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
@login_required
@editor_required
def index():
    if request.method == "POST":
        # Query users
        cur = db.connection.cursor()
        cur.execute('SELECT id FROM users')
        rows = cur.fetchall()
        cur.close()

        persons = []
        for row in rows:
            person = []
            person.append(row[0])
            status = request.form.get(str(row[0]))
            person.append(status)
            if status == "entschuldigt":
                person.append(request.form.get("reason-" + str(row[0])))
            persons.append(person)

        print(persons)

        return redirect("/")
    else:
        # Query users
        cur = db.connection.cursor()
        cur.execute('SELECT * FROM users')
        rows = cur.fetchall()
        print(rows)
        cur.close()

        return render_template("/admin/edit-today.html", persons=rows)


@app.route("/create_user", methods=["GET", "POST"])
@login_required
@admin_required
def create_user():
    """ Create new user or manage users """
    if request.method == "POST":
        username = request.form.get("username")
        usertype = request.form.get("usertype")
        notice = request.form.get("notice")

        # Create new user in database
        cur = db.connection.cursor()
        cur.execute('INSERT INTO users (username, hash, type, blocked, notice) VALUES (%s, "PASSWORD", %s, 0, %s)',
                    (username, usertype, notice))
        query = "CREATE TABLE " + username + " (id INT NOT NULL, user_id INT NOT NULL, status TEXT NOT NULL, reason TEXT NULL, PRIMARY KEY (id))"
        cur.execute(query)
        db.connection.commit()
        cur.close()

        return redirect('/create_user')
    else:
        # Query users
        cur = db.connection.cursor()
        cur.execute('SELECT * FROM users')
        rows = cur.fetchall()
        print(rows)
        cur.close()

        return render_template("/admin/admin-users.html", users=rows)


@app.route("/delete_user", methods=["POST"])
@login_required
@admin_required
def delete_user():
    """ Delete a user from the database """
    user_id = request.form.get("user_id")

    cur = db.connection.cursor()
    cur.execute('SELECT username FROM users WHERE id = %s', [user_id])
    rows = cur.fetchone()
    cur.execute('DELETE FROM users WHERE id = %s', [user_id])
    db.connection.commit()
    query = "DROP TABLE " + rows[0]
    cur.execute(query)
    cur.close()

    return '', 204


@app.route('/login', methods=["GET", "POST"])
def login():
    """Check for password and username and if user is newly created."""

    if request.method == "POST":
        # If user account is newly created
        if request.form.get("first_login"):
            # Check if both passwords are provided
            if not request.form.get("new_password"):
                flash("Bitte gebe ein neues Passwort ein!")
                return render_template("first-login.html")
            elif not request.form.get("confirmation"):
                flash("Bitte gebe die Bestätigung ein!")
                return render_template("first-login.html")

            # Check if both passwords are the same
            if request.form.get("new_password") != request.form.get("confirmation"):
                flash("Beide Passwörter stimmen nicht überein!")
                return render_template("first-login.html")

            # Update password in database
            cur = db.connection.cursor()
            cur.execute('UPDATE users SET hash = %s WHERE id = %s',
                        (generate_password_hash(request.form.get("confirmation")), session["user_id"]))
            db.connection.commit()
            cur.close()

            # Redirect to main page
            return redirect("/")

        username = request.form.get("username")
        password = request.form.get("password")

        # Ensure username was submitted
        if not username:
            flash("Bitte gebe einen Benutzernamen ein!")
            return render_template("login.html")

        # Ensure password was submitted
        elif not password:
            flash("Bitte gebe einen Passwort ein!")
            return render_template("login.html")

        # Query database for username
        cur = db.connection.cursor()
        cur.execute('SELECT * FROM users WHERE username = %s', [username])
        rows = cur.fetchone()
        cur.close()

        # Check if username exists
        if not rows:
            flash("Falscher Benutzername oder falsches Passwort!")
            return render_template("login.html")

        # Check if user is a newly created account
        if rows[2] == "PASSWORD":
            session["user_id"] = rows[0]
            session["user_type"] = rows[3]
            return render_template("first-login.html")

        # Ensure password is correct
        if not check_password_hash(rows[2], password):
            flash("Falscher Benutzername oder falsches Passwort!")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]

        # Remeber user account type
        session["user_type"] = rows[3]

        # Redirect user to home page
        return redirect("/")
    else:
        session.clear()
        return render_template("login.html")


if __name__ == '__main__':
    app.run(debug=True)
