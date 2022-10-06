import locale
from flask import Flask, render_template, session, redirect, request, flash
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash, generate_password_hash
from flask_session import Session
from datetime import datetime
from flask_assets import Environment, Bundle

from decorated_functions import login_required, editor_required, admin_required
from helpers import history_get_dates

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

assets = Environment(app)
assets.url = app.static_url_path

# Scss files
scss = Bundle(
    "assets/main.scss",
    filters="libsass",
    output="css/scss-generated.css"
)
assets.register("scss_all", scss)


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


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
                        (generate_password_hash(request.form.get("confirmation")), request.form.get("first_login")))
            db.connection.commit()
            cur.close()

            session["user_id"] = request.form.get("first_login")

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
        cur.execute('SELECT * FROM users WHERE username = %s AND deleted = 0', [username])
        row = cur.fetchone()
        cur.close()

        # Check if username exists
        if not row:
            flash("Falscher Benutzername oder ungültiges Passwort!")
            return render_template("login.html")

        # Check if user is newly created
        if row[7] == 1:
            session["user_type"] = row[3]
            return render_template("first-login.html", user_id=row[0])

        # Ensure password was submitted
        if not password:
            flash("Bitte gebe einen Passwort ein!")
            return render_template("login.html")

        # Ensure password is correct
        if not check_password_hash(row[1], password):
            flash("Falscher Benutzername oder ungültiges Passwort!")
            return render_template("login.html")

        if row[6] == 1:
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


@app.route("/")
@login_required
def index():
    """
        Displays that today exists no sv, or it hasn't been created yet or redirects to /history.
    """

    # # If user has higher privileges, redirect
    if not session.get("user_type") == "Normal":
        return redirect("/a")

    cur = db.connection.cursor()

    cur.execute('SELECT id FROM history WHERE date = %s', [datetime.today().strftime('%Y-%m-%d')])
    check = cur.fetchone()

    # Check if a session was created today
    if not check:
        return render_template("/normal/today.html")
    else:
        return redirect("/history")


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
            cur.close()

            return render_template("/admin/edit-today.html", persons=rows, status=2)

        if request.form.get("cancelled"):
            cur = db.connection.cursor()
            cur.execute('INSERT INTO history (cancelled, date) VALUES (1, %s)', [datetime.today().strftime('%Y-%m-%d')])
            db.connection.commit()
            cur.close()
            return redirect("/history")

        # Query users
        cur = db.connection.cursor()
        cur.execute('SELECT id FROM users')
        rows = cur.fetchall()

        # Get id, status ("Entschuldigt", "Fehlend", "Anwesend") and reason (if "Entschuldigt") from all users.
        persons = []
        for row in rows:
            person = [row[0]]

            status = request.form.get(str(row[0]))
            person.append(status)

            # If Entschuldigt get reason and append
            if status == "Entschuldigt":
                person.append(request.form.get("reason-" + str(row[0])))

            persons.append(person)

        # Get the non-elected person names.
        non_elected_persons = request.form.getlist("non_name")
        other_persons = request.form.getlist("other_name")

        db.connection.commit()

        # Create new history log in history_data table with users status, reason (If "Entschuldigt").
        for person in persons:
            # If user has a reason, submit it to table.
            if len(person) == 3:
                cur.execute('INSERT INTO history (date, type, user_id, status, reason)'
                            ' VALUES (%s, %s, %s, %s, %s)',
                            [datetime.today().strftime('%Y-%m-%d'), "elected", person[0], person[1], person[2]])
            else:
                cur.execute(
                    'INSERT INTO history (date, type, user_id, status)'
                    ' VALUES (%s, %s, %s, %s)',
                    [datetime.today().strftime('%Y-%m-%d'), "elected", person[0], person[1]])

        # Create new history log with non-elected person ("Freiwillige Personen") names
        if non_elected_persons:
            for person in non_elected_persons:
                cur.execute('INSERT INTO history (date, type, other_name)'
                            ' VALUES (%s, %s, %s)', [datetime.today().strftime('%Y-%m-%d'), "not_elected", person])

        # Create new history log with other person (other people than "Freiwillige Personen") names
        if other_persons:
            for person in other_persons:
                cur.execute('INSERT INTO history (date, type, other_name)'
                            ' VALUES (%s, %s, %s)', [datetime.today().strftime('%Y-%m-%d'), "other_person", person])

        db.connection.commit()
        cur.close()

        return redirect("/")
    else:
        cur = db.connection.cursor()
        cur.execute('SELECT id FROM history WHERE date = %s', [datetime.today().strftime('%Y-%m-%d')])
        check = cur.fetchone()
        cur.close()

        # Check if a session was created today
        if not check:
            return render_template("/admin/edit-today.html", status=0)
        else:
            return redirect("/history")


@app.route("/users")
@login_required
def users():
    """
        Show all persons
    """

    if session.get("user_type") == "Admin":
        return redirect("/a_create_user")

    # Query users
    cur = db.connection.cursor()
    cur.execute('SELECT * FROM users')
    rows = cur.fetchall()

    # Get an id from all users
    cur.execute('SELECT id FROM users ORDER BY id')
    ids = cur.fetchall()

    # Count their status ("Anwesend", "Fehlend", "Entschuldigt")
    status = []
    for user_id in ids:
        row = []
        cur.execute('SELECT COUNT(status) FROM history WHERE user_id = %s AND status = %s', [user_id, "Anwesend"])
        anwesend = cur.fetchone()
        row.append(anwesend)

        cur.execute('SELECT COUNT(status) FROM history WHERE user_id = %s AND status = %s', [user_id, "Fehlend"])
        fehlend = cur.fetchone()
        row.append(fehlend)

        cur.execute('SELECT COUNT(status) FROM history WHERE user_id = %s AND status = %s',
                    [user_id, "Entschuldigt"])
        entschuldigt = cur.fetchone()

        row.append(entschuldigt)
        status.append(row)

    # Count non-elected ("Freiwillige Personen") names
    cur.execute('SELECT DISTINCT(other_name), COUNT(other_name) '
                'FROM history WHERE type = %s '
                'GROUP BY other_name', ["not_elected"])
    other_persons = cur.fetchall()

    cur.close()

    return render_template("/normal/users.html", users=rows, status=status,
                           not_elected_persons=other_persons)


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
        cur.execute('INSERT INTO users (hash, username, type, office, notice) '
                    'VALUES (%s, %s, %s, %s, %s)',
                    ("PASSWORD", username, usertype, office, notice))
        db.connection.commit()
        cur.close()

        return redirect('/a_create_user')
    else:
        # Query users
        cur = db.connection.cursor()
        cur.execute('SELECT * FROM users WHERE deleted = 0')
        rows = cur.fetchall()

        # Get an id from all users
        cur.execute('SELECT id FROM users WHERE deleted = 0 ORDER BY id')
        ids = cur.fetchall()

        # Count their status ("Anwesend", "Fehlend", "Entschuldigt")
        status = []
        for user_id in ids:
            row = []
            cur.execute('SELECT COUNT(status) FROM history WHERE user_id = %s AND status = %s',
                        [user_id, "Anwesend"])
            anwesend = cur.fetchone()
            row.append(anwesend)

            cur.execute('SELECT COUNT(status) FROM history WHERE user_id = %s AND status = %s',
                        [user_id, "Fehlend"])
            fehlend = cur.fetchone()
            row.append(fehlend)

            cur.execute('SELECT COUNT(status)  FROM history WHERE user_id = %s AND status = %s',
                        [user_id, "Entschuldigt"])
            entschuldigt = cur.fetchone()

            row.append(entschuldigt)
            status.append(row)

        # Count non-elected ("Freiwillige Personen") names
        cur.execute('SELECT DISTINCT(other_name), COUNT(other_name) '
                    'FROM history WHERE type = %s '
                    'GROUP BY other_name', ["not_elected"])
        not_elected_persons = cur.fetchall()

        cur.close()

        return render_template("/admin/admin-users.html", users=rows, status=status,
                               not_elected_persons=not_elected_persons)


@app.route("/history")
@login_required
def history():
    """
        Shows all past sv sessions.
    """

    # Set strftime to german
    locale.setlocale(locale.LC_ALL, 'de_DE.utf8')

    history_date = request.args.get("date")

    cur = db.connection.cursor()

    # If history id is not given
    if not history_date:
        # Get latest sv session
        cur.execute('SELECT date, cancelled FROM history ORDER BY id DESC LIMIT 1')
        history = cur.fetchone()

        # If there is no sv session
        if not history:
            if not session.get("user_type") == "Normal":
                return render_template("/admin/admin-history.html", status=1)
            return render_template("/normal/history.html", status=1)
    else:
        cur.execute('SELECT date, cancelled FROM history WHERE date = %s', [history_date])
        history = cur.fetchone()

        # If there is no sv session
        if not history:
            # Get latest sv session
            cur.execute('SELECT date, cancelled FROM history ORDER BY id DESC LIMIT 1')
            history = cur.fetchone()

            # If there is no sv session
            if not history:
                if not session.get("user_type") == "Normal":
                    return render_template("/admin/admin-history.html", status=1)
                return render_template("/normal/history.html", status=1)

    # If sv session is cancelled
    if history[1] == 1:

        # Get data for top bar
        current_day, last_day, next_day = history_get_dates(history)

        if not session.get("user_type") == "Normal":
            return render_template("/admin/admin-history.html", status=0,
                                   current_day=current_day.strftime('%A, %-d.%-m.%Y'), next_day=next_day,
                                   last_day=last_day)
        return render_template("/normal/history.html", status=0,
                               current_day=current_day.strftime('%A, %-d.%-m.%Y'), next_day=next_day,
                               last_day=last_day)

    # Get all elected persons
    cur.execute(
        "SELECT user_id, status, reason FROM history WHERE type = 'elected' AND date = %s",
        [history[0]])
    persons_query = cur.fetchall()

    # Appends each person in person_query with its name and office
    persons = []
    for person in persons_query:
        row = [person[0], person[1], person[2]]

        cur.execute("SELECT username, office FROM users WHERE id = %s", [person[0]])
        username = cur.fetchone()

        row.append(username[0])
        row.append(username[1])
        persons.append(row)

    # Get all voluntary persons
    cur.execute("SELECT other_name FROM history WHERE type = 'not_elected' AND date = %s",
                [history[0]])
    not_elected_persons = cur.fetchall()

    # Get all other persons
    cur.execute("SELECT other_name FROM history WHERE type = 'other_person' AND date = %s",
                [history[0]])
    other_persons = cur.fetchall()

    cur.close()

    # Get data for top bar
    current_day, last_day, next_day = history_get_dates(history)

    if not session.get("user_type") == "Normal":
        return render_template("/admin/admin-history.html", status=2, not_elected_persons=not_elected_persons,
                               other_persons=other_persons, persons=persons,
                               current_day=current_day.strftime('%A, %-d.%-m.%Y'), next_day=next_day, last_day=last_day,
                               history_date=history[0])
    return render_template("/normal/history.html", status=2, not_elected_persons=not_elected_persons,
                           other_persons=other_persons, persons=persons,
                           current_day=current_day.strftime('%A, %-d.%-m.%Y'), next_day=next_day, last_day=last_day,
                           history_date=history[0])


@app.route("/a_change_history", methods=["POST"])
@login_required
@editor_required
def change_history():
    """
        ADMIN OR EDITOR REQUIRED
        Shows all past sv sessions.
    """

    history_date = request.form.get("history_date")

    cur = db.connection.cursor()

    # Get all persons from given session
    cur.execute('SELECT user_id FROM history WHERE type = %s AND date = %s',
                ["elected", history_date])
    persons = cur.fetchall()

    # Edit given session
    for person in persons:
        status = request.form.get(str(person[0]))

        if status == "Entschuldigt":
            reason = request.form.get("reason-" + str(person[0]))

            cur.execute('UPDATE history SET status = %s, reason = %s WHERE user_id = %s AND date = %s',
                        [status, reason, person[0], history_date])

        else:
            cur.execute('UPDATE history SET status = %s, reason = NULL WHERE user_id = %s AND date = %s',
                        [status, person[0], history_date])

    db.connection.commit()

    return redirect("/history")


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
    locale.setlocale(locale.LC_ALL, 'de_DE.utf8')
    cur.execute('SELECT date FROM history GROUP BY date ORDER BY date DESC')
    dates = cur.fetchall()

    # Go through each date from the dates list to add user's history from each date.
    history = []
    for date in dates:
        row = []

        # Select information about the SV day from the current date.
        cur.execute('SELECT status, reason FROM history '
                    'WHERE date = %s AND user_id = %s',
                    [date[0].strftime('%Y-%m-%d'), user_id])
        query = cur.fetchone()

        # If current SV day has no information, break for loop
        if not query:
            continue

        # Summarize the information and append it to history list
        row.append(date[0].strftime('%A, %-d.%-m.%Y'))
        row.append(query)
        history.append(row)

    cur.close()

    return render_template("/normal/user_history.html", history=history, person=name[0])


@app.route("/delete_user", methods=["POST"])
@login_required
@admin_required
def delete_user():
    """ Delete a user from the database """
    user_id = request.form.get("user_id")

    cur = db.connection.cursor()
    cur.execute('UPDATE users SET deleted = 1 WHERE id = %s', [user_id])
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
    cur.execute('UPDATE users SET block = 1 WHERE id = %s', [user_id])
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
    cur.execute('UPDATE users SET block = 0 WHERE id = %s', [user_id])
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


if __name__ == '__main__':
    app.run(debug=True)
