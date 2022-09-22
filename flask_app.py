import locale
from flask import Flask, render_template, session, redirect, request, flash
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash, generate_password_hash
from flask_session import Session
from functools import wraps
from datetime import datetime

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
        else:
            cur = db.connection.cursor()

            # Select something in users table from current user_id
            cur.execute('SELECT username FROM users WHERE id = %s', [session.get("user_id")])
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
        if session.get("user_type") != "Admin":
            return redirect("/")
        return f(*args, **kwargs)

    return decorated_function


def editor_required(f):
    """
    Decorate routes to require editor type account or higher.

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


@app.route("/", methods=["GET"])
@login_required
def index():
    if not session.get("user_type") == "Normal":
        return redirect("/a")

    cur = db.connection.cursor()

    day = datetime.today().strftime('%Y-%m-%d')
    cur.execute('SELECT id FROM history WHERE date = %s', [day])
    history = cur.fetchone()

    if not history:
        return render_template("/normal/today.html")
    else:
        return redirect("/history")


@app.route("/history")
@login_required
def history():
    if session.get("user_type") == "Bearbeiter" or session.get("user_type") == "Admin":
        return redirect("/a_history")

    locale.setlocale(locale.LC_ALL, 'de_DE.utf8')

    id = request.args.get("history_id")

    cur = db.connection.cursor()

    if not id:
        day = datetime.today().strftime('%Y-%m-%d')
        cur.execute('SELECT id, date, cancelled FROM history WHERE date = %s', [day])
        history = cur.fetchone()

        if not history:
            return render_template("/normal/history.html", status=1)
    else:
        cur.execute('SELECT id, date, cancelled FROM history WHERE id = %s', [id])
        history = cur.fetchone()

        if not history:
            day = datetime.today().strftime('%Y-%m-%d')
            cur.execute('SELECT id, date, cancelled FROM history WHERE date = %s', [day])
            history = cur.fetchone()

            if not history:
                return render_template("/normal/history.html", status=1)

    if history[2] == 1:
        current_day = history[1]
        last_day = history[0] - 1
        next_day = history[0] + 1

        return render_template("/normal/history.html", status=0,
                               current_day=current_day.strftime('%A, %-d.%-m.%Y'), next_day=next_day,
                               last_day=last_day)

    cur.execute(
        "SELECT user_id, username, status, reason FROM history_data WHERE person_type = 'elected' AND history_id = %s",
        [history[0]])
    persons = cur.fetchall()
    cur.execute("SELECT non_elected_name FROM history_data WHERE person_type = 'not_elected' AND history_id = %s",
                [history[0]])
    not_elected_persons = cur.fetchall()
    cur.execute("SELECT non_elected_name FROM history_data WHERE person_type = 'other_person' AND history_id = %s",
                [history[0]])
    other_persons = cur.fetchall()

    current_day = history[1]
    last_day = history[0] - 1
    next_day = history[0] + 1

    cur.close()

    return render_template("/normal/history.html", status=2, not_elected_persons=not_elected_persons,
                           other_persons=other_persons, persons=persons,
                           current_day=current_day.strftime('%A, %-d.%-m.%Y'), next_day=next_day, last_day=last_day,
                           history_id=history[0])


@app.route("/a", methods=["GET", "POST"])
@login_required
@editor_required
def a_index():
    """
    ADMIN OR EDITOR REQUIRED

    Add SV day, select status from users, add non-elected persons and submit it to the database.
    """

    # Get data and send it to database
    if request.method == "POST":
        if request.form.get("new_day"):
            # Query users
            cur = db.connection.cursor()
            cur.execute('SELECT * FROM users')
            rows = cur.fetchall()
            print(rows)
            cur.close()

            return render_template("/admin/edit-today.html", persons=rows, status=2)

        if request.form.get("cancelled"):
            cur = db.connection.cursor()
            cur.execute('INSERT INTO history (cancelled, date) VALUES (1, %s)', [datetime.today().strftime('%Y-%m-%d')])
            db.connection.commit()
            cur.close()
            return render_template("/admin/edit-today.html", status=1)

        # Query users
        cur = db.connection.cursor()
        cur.execute('SELECT id FROM users')
        rows = cur.fetchall()

        # Get id, status ("Entschuldigt", "Fehlend", "Anwesend") and reason (if "Entschuldigt") from all users.
        persons = []
        for row in rows:
            person = []

            # Append id
            person.append(row[0])

            status = request.form.get(str(row[0]))
            person.append(status)

            # If Entschuldigt get reason and append
            if status == "Entschuldigt":
                person.append(request.form.get("reason-" + str(row[0])))

            persons.append(person)

        # Get the non-elected person names.
        non_elected_persons = request.form.getlist("non_name")
        other_persons = request.form.getlist("other_name")

        # Debug
        # cur.execute('SET TIMESTAMP=unix_timestamp("2022-04-01")')

        # Create new day in database.
        cur.execute('INSERT INTO history (cancelled, date) VALUES (0, %s)', [datetime.today().strftime('%Y-%m-%d')])
        db.connection.commit()

        # Debug
        # cur.execute('SELECT id FROM history WHERE date = %s', ["2022-04-01"])

        # Get id of current SV day.
        cur.execute('SELECT id FROM history WHERE date = %s', [datetime.today().strftime('%Y-%m-%d')])

        history_id = cur.fetchone()

        # Debug
        cur.execute('SET TIMESTAMP=unix_timestamp("default")')

        # Create new history log in history_data table with users status, reason (If "Entschuldigt").
        for person in persons:

            # Get username of current person
            cur.execute('SELECT username FROM users WHERE id = %s', [person[0]])
            username = cur.fetchone()

            # If user has a reason, submit it to table.
            if len(person) == 3:
                cur.execute('INSERT INTO history_data (person_type, history_id, username, user_id, status, reason)'
                            ' VALUES ("elected", %s, %s, %s, %s, %s)',
                            [history_id, username[0], person[0], person[1], person[2]])
            else:
                cur.execute(
                    'INSERT INTO history_data (person_type, history_id, username, user_id, status)'
                    ' VALUES ("elected", %s, %s, %s, %s)', [history_id, username[0], person[0], person[1]])

        # Create new history log with non-elected person ("Freiwillige Personen") names
        print(non_elected_persons)
        if non_elected_persons:
            for person in non_elected_persons:
                print(person)
                cur.execute('INSERT INTO history_data (person_type, history_id, non_elected_name)'
                            ' VALUES ("not_elected", %s, %s)', [history_id, person])

        # Create new history log with other person (other people than "Freiwilige Personen") names
        if other_persons:
            for person in other_persons:
                cur.execute('INSERT INTO history_data (person_type, history_id, non_elected_name)'
                            ' VALUES ("other_person", %s, %s)', [history_id, person])

        db.connection.commit()
        cur.close()

        return redirect("/")
    else:
        cur = db.connection.cursor()
        cur.execute('SELECT cancelled FROM history WHERE date = %s', [datetime.today().strftime('%Y-%m-%d')])
        check = cur.fetchone()
        cur.close()

        if not check:
            return render_template("/admin/edit-today.html", status=0)
        else:
            return redirect("/a_history")


@app.route("/create_user", methods=["GET"])
@login_required
def create_user():
    if not session.get("user_type") == "Admin":
        # Query users
        cur = db.connection.cursor()
        cur.execute('SELECT * FROM users')
        rows = cur.fetchall()

        # Get an id from all users
        cur.execute('SELECT id FROM users ORDER BY id ASC')
        ids = cur.fetchall()

        # Count their status ("Anwesend", "Fehlend", "Entschuldigt")
        status = []
        for user_id in ids:
            row = []
            cur.execute('SELECT COUNT(status) FROM history_data WHERE user_id = %s AND status = "Anwesend"', [user_id])
            anwesend = cur.fetchone()
            row.append(anwesend)

            cur.execute('SELECT COUNT(status) FROM history_data WHERE user_id = %s AND status = "Fehlend"', [user_id])
            fehlend = cur.fetchone()
            row.append(fehlend)

            cur.execute('SELECT COUNT(status)  FROM history_data WHERE user_id = %s AND status = "Entschuldigt"',
                        [user_id])
            entschuldigt = cur.fetchone()

            row.append(entschuldigt)
            status.append(row)

        # Count non-elected ("Freiwillige Personen") names
        cur.execute('SELECT DISTINCT(non_elected_name), COUNT(non_elected_name) '
                    'FROM history_data WHERE person_type = "not_elected" '
                    'GROUP BY non_elected_name')
        not_elected_persons = cur.fetchall()

        cur.close()

        return render_template("/normal/users.html", users=rows, status=status,
                               not_elected_persons=not_elected_persons)
    else:
        return redirect("/a_create_user")


@app.route("/a_change_history", methods=["POST"])
@login_required
@editor_required
def change_history():
    history_id = request.form.get("history_id")

    cur = db.connection.cursor()

    cur.execute('SELECT user_id FROM history_data WHERE person_type = "elected" AND history_id = %s', [history_id])
    persons = cur.fetchall()

    for person in persons:
        status = request.form.get(str(person[0]))

        if status == "Entschuldigt":
            reason = request.form.get("reason-" + str(person[0]))

            cur.execute('UPDATE history_data SET status = %s, reason = %s WHERE user_id = %s AND history_id = %s',
                        [status, reason, person[0], history_id])

        else:
            cur.execute('UPDATE history_data SET status = %s, reason = NULL WHERE user_id = %s AND history_id = %s',
                        [status, person[0], history_id])

    db.connection.commit()

    return redirect("/a_history")


@app.route("/a_history")
@login_required
@editor_required
def admin_history():
    locale.setlocale(locale.LC_ALL, 'de_DE.utf8')

    id = request.args.get("history_id")

    cur = db.connection.cursor()

    if not id:
        day = datetime.today().strftime('%Y-%m-%d')
        cur.execute('SELECT id, date, cancelled FROM history WHERE date = %s', [day])
        history = cur.fetchone()

        if not history:
            return render_template("/admin/admin-history.html", status=1)
    else:
        cur.execute('SELECT id, date, cancelled FROM history WHERE id = %s', [id])
        history = cur.fetchone()

        if not history:
            day = datetime.today().strftime('%Y-%m-%d')
            cur.execute('SELECT id, date, cancelled FROM history WHERE date = %s', [day])
            history = cur.fetchone()

            if not history:
                return render_template("/admin/admin-history.html", status=1)

    if history[2] == 1:
        current_day = history[1]
        last_day = history[0] - 1
        next_day = history[0] + 1

        return render_template("/admin/admin-history.html", status=0,
                               current_day=current_day.strftime('%A, %-d.%-m.%Y'), next_day=next_day,
                               last_day=last_day)

    cur.execute(
        "SELECT user_id, username, status, reason FROM history_data WHERE person_type = 'elected' AND history_id = %s",
        [history[0]])
    persons = cur.fetchall()
    cur.execute("SELECT non_elected_name FROM history_data WHERE person_type = 'not_elected' AND history_id = %s",
                [history[0]])
    not_elected_persons = cur.fetchall()
    cur.execute("SELECT non_elected_name FROM history_data WHERE person_type = 'other_person' AND history_id = %s",
                [history[0]])
    other_persons = cur.fetchall()

    current_day = history[1]
    last_day = history[0] - 1
    next_day = history[0] + 1

    cur.close()

    return render_template("/admin/admin-history.html", status=2, not_elected_persons=not_elected_persons,
                           other_persons=other_persons, persons=persons,
                           current_day=current_day.strftime('%A, %-d.%-m.%Y'), next_day=next_day, last_day=last_day,
                           history_id=history[0])


@app.route("/user_history", methods=["POST"])
@login_required
def user_history():
    """ Show history of a user """

    user_id = request.form.get("user_id")

    cur = db.connection.cursor()

    # Get name of user
    cur.execute('SELECT username FROM users WHERE id = %s', [user_id])
    name = cur.fetchone()

    # Select ids and dates from history table in descending order and set date names to german.
    cur.execute('SET lc_time_names = "de_DE"')
    cur.execute('SELECT id, DATE_FORMAT(date, "%W, %e.%c.%y") FROM history ORDER BY date DESC')
    dates = cur.fetchall()

    # Go through each date from the dates list to add user's history from each date.
    history = []
    for date in dates:
        row = []

        # Select information about the SV day from the current date.
        cur.execute('SELECT status, reason FROM history_data '
                    'WHERE history_id = %s AND user_id = %s',
                    [date[0], user_id])
        query = cur.fetchone()

        # If current SV day has no information, break for loop
        if not query:
            break

        # Summarize the information and append it to history list
        row.append(date[1])
        row.append(query)
        history.append(row)

    cur.close()

    return render_template("/normal/user_history.html", history=history, person=name[0])


@app.route("/a_create_user", methods=["GET", "POST"])
@login_required
@admin_required
def admin_create_user():
    """
    ADMIN REQUIRED

    Create new user or manage users
    """

    if request.method == "POST":
        username = request.form.get("username")
        usertype = request.form.get("usertype")
        office = request.form.get("user_office")
        notice = request.form.get("notice")

        # Create new user in database
        cur = db.connection.cursor()
        cur.execute('INSERT INTO users (username, hash, type, blocked, notice, office, reset) '
                    'VALUES (%s, "PASSWORD", %s, 0, %s, %s, 1)',
                    (username, usertype, notice, office))
        db.connection.commit()
        cur.close()

        return redirect('/a_create_user')
    else:
        # Query users
        cur = db.connection.cursor()
        cur.execute('SELECT * FROM users')
        rows = cur.fetchall()

        # Get an id from all users
        cur.execute('SELECT id FROM users ORDER BY id ASC')
        ids = cur.fetchall()

        # Count their status ("Anwesend", "Fehlend", "Entschuldigt")
        status = []
        for user_id in ids:
            row = []
            cur.execute('SELECT COUNT(status) FROM history_data WHERE user_id = %s AND status = "Anwesend"', [user_id])
            anwesend = cur.fetchone()
            row.append(anwesend)

            cur.execute('SELECT COUNT(status) FROM history_data WHERE user_id = %s AND status = "Fehlend"', [user_id])
            fehlend = cur.fetchone()
            row.append(fehlend)

            cur.execute('SELECT COUNT(status)  FROM history_data WHERE user_id = %s AND status = "Entschuldigt"',
                        [user_id])
            entschuldigt = cur.fetchone()

            row.append(entschuldigt)
            status.append(row)

        # Count non-elected ("Freiwillige Personen") names
        cur.execute('SELECT DISTINCT(non_elected_name), COUNT(non_elected_name) '
                    'FROM history_data WHERE person_type = "not_elected" '
                    'GROUP BY non_elected_name')
        not_elected_persons = cur.fetchall()

        cur.close()

        return render_template("/admin/admin-users.html", users=rows, status=status,
                               not_elected_persons=not_elected_persons)


@app.route("/delete_user", methods=["POST"])
@login_required
@admin_required
def delete_user():
    """ Delete a user from the database """
    user_id = request.form.get("user_id")

    cur = db.connection.cursor()
    cur.execute('UPDATE users SET reset = 1 WHERE id = %s', [user_id])
    cur.execute('DELETE FROM users WHERE id = %s', [user_id])
    db.connection.commit()
    cur.close()

    return '', 204


@app.route("/reset_user", methods=["POST"])
@login_required
@admin_required
def reset_user():
    """ Reset password of user """
    user_id = request.form.get("user_id")

    cur = db.connection.cursor()
    cur.execute('UPDATE users SET reset = 1 WHERE id = %s', [user_id])
    db.connection.commit()
    cur.close()

    return '', 204


@app.route("/block_user", methods=["POST"])
@login_required
@admin_required
def block_user():
    """ Block user """
    user_id = request.form.get("user_id")

    cur = db.connection.cursor()
    cur.execute('UPDATE users SET blocked = 1 WHERE id = %s', [user_id])
    db.connection.commit()
    cur.close()

    return '', 204


@app.route("/unblock_user", methods=["POST"])
@login_required
@admin_required
def unblock_user():
    """ Unblock user """
    user_id = request.form.get("user_id")

    cur = db.connection.cursor()
    cur.execute('UPDATE users SET blocked = 0 WHERE id = %s', [user_id])
    db.connection.commit()
    cur.close()

    return '', 204


@app.route("/change_notice", methods=["POST"])
@login_required
@admin_required
def change_notice():
    """ Change notice of user """
    user_id = request.form.get("user_id")
    notice = request.form.get("notice")

    cur = db.connection.cursor()
    cur.execute('UPDATE users SET notice = %s WHERE id = %s', [notice, user_id])
    db.connection.commit()
    cur.close()

    return redirect("/a_create_user")


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
            cur.execute('UPDATE users SET hash = %s, reset = 0 WHERE id = %s',
                        (generate_password_hash(request.form.get("confirmation")), session["user_id"]))
            db.connection.commit()
            cur.close()

            # Redirect to main page
            return redirect("/a")

        username = request.form.get("username")
        password = request.form.get("password")

        # Ensure username was submitted
        if not username:
            flash("Bitte gebe einen Benutzernamen ein!")
            return render_template("login.html")

        # Query database for username
        cur = db.connection.cursor()
        cur.execute('SELECT * FROM users WHERE username = %s', [username])
        row = cur.fetchone()
        cur.close()

        # Check if username exists
        if not row:
            flash("Falscher Benutzername oder ungültiges Passwort!")
            return render_template("login.html")

        # Check if user is newly created
        if row[7] == 1:
            session["user_id"] = row[0]
            session["user_type"] = row[3]
            return render_template("first-login.html")

        # Ensure password was submitted
        if not password:
            flash("Bitte gebe einen Passwort ein!")
            return render_template("login.html")

        # Ensure password is correct
        if not check_password_hash(row[2], password):
            flash("Falscher Benutzername oder ungültiges Passwort!")
            return render_template("login.html")

        if row[4] == 1:
            flash("Dein Konto wurde geblockt!")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = row[0]

        # Remember user account type
        session["user_type"] = row[3]

        # Redirect user to home page
        return redirect("/a")
    else:
        session.clear()
        return render_template("login.html")


if __name__ == '__main__':
    app.run(debug=True)
