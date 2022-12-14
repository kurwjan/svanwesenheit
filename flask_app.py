import locale
from flask import Flask, render_template, session, redirect, request, flash
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash, generate_password_hash
from flask_session import Session
from datetime import datetime
#from flask_assets import Environment, Bundle

from decorated_functions import login_required, edit_permissions_required, admin_required
from helpers import history_get_dates, get_type

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

#assets = Environment(app)
#assets.url = app.static_url_path

# Scss files
#scss = Bundle(
#    "assets/main.scss",
#    filters="libsass",
#    output="css/scss-generated.css"
#)
#assets.register("scss_all", scss)


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route('/manage_user', methods=["POST"])
def manage_user():

    cur = db.connection.cursor()
    cur.execute('SELECT * FROM users WHERE id = %s', [request.form.get("user_id")])
    user = cur.fetchone()

    return render_template("manage_user.html", user=user)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Check for password and username and if user is newly created."""

    if request.method == "POST":
        # If user account is newly created
        if request.form.get("create_password"):
            # Check if both passwords are provided
            if not request.form.get("new_password"):
                flash("Bitte gebe ein neues Passwort ein!")
                return render_template("create_password.html")
            elif not request.form.get("confirmation"):
                flash("Bitte gebe die Best??tigung ein!")
                return render_template("create_password.html")

            # Check if both passwords are the same
            if request.form.get("new_password") != request.form.get("confirmation"):
                flash("Beide Passw??rter stimmen nicht ??berein!")
                return render_template("create_password.html")

            # Update password in database
            cur = db.connection.cursor()
            cur.execute('UPDATE users SET hash = %s, reset = 0 WHERE id = %s',
                        (generate_password_hash(request.form.get("confirmation")), request.form.get("create_password")))
            db.connection.commit()
            cur.close()

            session["user_id"] = request.form.get("create_password")

            # Redirect to main page
            return redirect("/")

        username = request.form.get("username")
        password = request.form.get("password")

        # Ensure username was submitted
        if not username:
            flash("Bitte gebe einen Benutzernamen ein!")
            return render_template("login.html")

        # Query database for username
        cur = db.connection.cursor()
        cur.execute('SELECT * FROM users WHERE loginname = %s AND deleted = 0', [username])
        user = cur.fetchone()
        cur.close()

        # Check if username exists
        if not user:
            flash("Falscher Benutzername oder ung??ltiges Passwort!")
            return render_template("login.html")

        # Check if user is newly created
        if user[7] == 1:
            session["user_type"] = user[3]
            return render_template("create_password.html", user_id=user[0])

        # Ensure password was submitted
        if not password:
            flash("Bitte gebe einen Passwort ein!")
            return render_template("login.html")

        # Ensure password is correct
        if not check_password_hash(user[1], password):
            flash("Falscher Benutzername oder ung??ltiges Passwort!")
            return render_template("login.html")

        if user[6] == 1:
            flash("Dein Konto wurde geblockt!")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = user[0]

        # Remember user account type
        session["user_type"] = user[3]

        # Redirect user to home page
        return redirect("/")
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
    if not get_type(session.get("user_id")) == "Nutzer":
        return redirect("/create_session")

    cur = db.connection.cursor()

    cur.execute('SELECT id FROM history WHERE date = %s', [datetime.today().strftime('%Y-%m-%d')])
    check = cur.fetchone()

    # Check if a session was created today
    if not check:
        return render_template("no_sv.html")
    else:
        return redirect("/history")


@app.route("/create_session", methods=["GET", "POST"])
@login_required
@edit_permissions_required
def create_session():
    """
    Needs editor permissions

    Adds/Changes SV day, select status from users, add non-elected persons and submit it to the database.
    """

    # Get data and send it to database
    if request.method == "POST":
        if request.form.get("new_day"):
            # Query users
            cur = db.connection.cursor()
            cur.execute('SELECT * FROM users WHERE deleted = 0')
            persons = cur.fetchall()
            cur.close()

            return render_template("create_session.html", persons=persons, status=1)

        if request.form.get("cancelled"):
            cur = db.connection.cursor()
            cur.execute('SELECT * FROM users WHERE deleted = 0')
            persons = cur.fetchall()
            db.connection.commit()
            cur.close()
            return render_template("create_cancelled_session.html", persons=persons)

        # Feature postponed
        # if request.form.get("change_cancelled_session"):
        #    # Query users
        #    cur = db.connection.cursor()
        #    cur.execute('SELECT * FROM users WHERE deleted = 0')
        #    rows = cur.fetchall()
        #    cur.close()
        #
        #    return render_template("/admin/create_session.html", persons=rows, status=2,
        #                           cancelled_date=request.form.get("change_cancelled_session"))

        cancelled_date = request.form.get("cancelled_date")

        date = cancelled_date if cancelled_date else datetime.today().strftime('%Y-%m-%d')

        # Query users
        cur = db.connection.cursor()

        cur.execute('SELECT id FROM history WHERE date = %s', [date])
        exists_session = cur.fetchone()

        if exists_session:
            return redirect("/")

        cur.execute('SELECT id FROM users WHERE deleted = 0')
        persons_query = cur.fetchall()

        if cancelled_date:
            cur.execute('DELETE FROM history WHERE date = %s', [cancelled_date])

        # Get id, status ("Entschuldigt", "Fehlend", "Anwesend") and reason (if "Entschuldigt") from all users.
        persons = []
        for person in persons_query:
            person = [person[0]]

            status = request.form.get(str(person[0]))
            person.append(status)

            # If Entschuldigt get reason and append
            if status == "Entschuldigt":
                person.append(request.form.get("reason-" + str(person[0])))

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
                            [date, "elected", person[0], person[1], person[2]])
            else:
                if request.form.get("create_cancelled_session"):
                    cur.execute(
                        'INSERT INTO history (date, type, user_id, status, cancelled)'
                        ' VALUES (%s, %s, %s, %s, 1)',
                        [date, "elected", person[0], person[1]])
                    continue

                cur.execute(
                    'INSERT INTO history (date, type, user_id, status)'
                    ' VALUES (%s, %s, %s, %s)',
                    [date, "elected", person[0], person[1]])

        # Create new history log with non-elected person ("Freiwillige Personen") names
        if non_elected_persons:
            for person in non_elected_persons:
                cur.execute('INSERT INTO history (date, type, other_name)'
                            ' VALUES (%s, %s, %s)', [date, "not_elected", person])

        # Create new history log with other person (other people than "Freiwillige Personen") names
        if other_persons:
            for person in other_persons:
                cur.execute('INSERT INTO history (date, type, other_name)'
                            ' VALUES (%s, %s, %s)', [date, "other_person", person])

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
            return render_template("create_session.html", status=0)
        else:
            return redirect("/history")


@app.route("/users", methods=["GET", "POST"])
@login_required
def users():
    """
    Create and manage new users or show all users.
    """

    if request.method == "POST":
        username = request.form.get("username")
        usertype = request.form.get("usertype")
        office = request.form.get("user_office")
        notice = request.form.get("notice")
        login_name = request.form.get("loginname")

        if not username:
            flash("Kein Anzeigename angegeben!")
            return redirect('/manage_users')

        if not login_name:
            flash("Kein Loginname angegeben!")
            return redirect('/manage_users')

        # Create new user in database
        cur = db.connection.cursor()
        cur.execute('INSERT INTO users (hash, username, type, office, notice, loginname) '
                    'VALUES (%s, %s, %s, %s, %s, %s)',
                    ("PASSWORD", username, usertype, office, notice, login_name))
        db.connection.commit()
        cur.close()

        return redirect('/users')
    else:
        # Query users
        cur = db.connection.cursor()
        cur.execute('SELECT * FROM users WHERE deleted = 0')
        users = cur.fetchall()

        # Get an id from all users
        cur.execute('SELECT id FROM users WHERE deleted = 0 ORDER BY id')
        ids = cur.fetchall()

        # Count their status ("Anwesend", "Fehlend", "Entschuldigt")
        status = []
        for user_id in ids:
            row = []
            cur.execute('SELECT COUNT(status) FROM history WHERE user_id = %s AND status = %s AND cancelled = 0',
                        [user_id, "Anwesend"])
            anwesend = cur.fetchone()
            row.append(anwesend)

            cur.execute('SELECT COUNT(status) FROM history WHERE user_id = %s AND status = %s',
                        [user_id, "Fehlend"])
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
        not_elected_persons = cur.fetchall()

        cur.close()

        if get_type(session.get("user_id")) == "Admin":
            return render_template("manage_users.html", users=users, status=status,
                                   not_elected_persons=not_elected_persons)
        return render_template("users.html", users=users, status=status,
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
        cur.execute('SELECT date, cancelled FROM history ORDER BY date DESC LIMIT 1')
        history = cur.fetchone()

        # If there is no sv session
        if not history:
            if not get_type(session.get("user_id")) == "Normal":
                return render_template("manage_history.html", status=1)
            return render_template("history.html", status=1)
    else:
        cur.execute('SELECT date, cancelled FROM history WHERE date = %s', [history_date])
        history = cur.fetchone()

        # If there is no sv session
        if not history:
            # Get latest sv session
            cur.execute('SELECT date, cancelled FROM history ORDER BY date DESC LIMIT 1')
            history = cur.fetchone()

            # If there is no sv session
            if not history:
                if not get_type(session.get("user_id")) == "Normal":
                    return render_template("manage_history.html", status=1)
                return render_template("history.html", status=1)

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

    # If sv session is cancelled
    if history[1] == 1:

        # Get data for top bar
        current_day, last_day, next_day = history_get_dates(history)

        if not get_type(session.get("user_id")) == "Nutzer":
            return render_template("manage_history.html", status=0,
                                   current_day=current_day.strftime('%A, %-d.%-m.%Y'), next_day=next_day,
                                   last_day=last_day, history_date=history[0], persons=persons)
        return render_template("history.html", status=0,
                               current_day=current_day.strftime('%A, %-d.%-m.%Y'), next_day=next_day,
                               last_day=last_day, history_date=history[0], persons=persons)

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

    if not get_type(session.get("user_id")) == "Nutzer":
        return render_template("manage_history.html", status=2, not_elected_persons=not_elected_persons,
                               other_persons=other_persons, persons=persons,
                               current_day=current_day.strftime('%A, %-d.%-m.%Y'), next_day=next_day, last_day=last_day,
                               history_date=history[0])
    return render_template("history.html", status=2, not_elected_persons=not_elected_persons,
                           other_persons=other_persons, persons=persons,
                           current_day=current_day.strftime('%A, %-d.%-m.%Y'), next_day=next_day, last_day=last_day,
                           history_date=history[0])


@app.route("/change_history", methods=["POST"])
@login_required
@edit_permissions_required
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


@app.route("/delete_history", methods=["POST"])
@login_required
@edit_permissions_required
def delete_history():
    """
        ADMIN OR EDITOR REQUIRED
        Deletes a session.
    """

    history_date = request.form.get("history_date")

    cur = db.connection.cursor()
    cur.execute('DELETE FROM history WHERE date = %s', [history_date])
    db.connection.commit()
    cur.close()

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
        cur.execute('SELECT status, reason, cancelled FROM history '
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

    return render_template("user_history.html", history=history, person=name[0])


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

    return redirect("/users")


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

    return '', 204


@app.route("/change_type", methods=["POST"])
@login_required
@admin_required
def change_type():
    """ Change type of user """
    user_id = request.form.get("user_id")
    type = request.form.get("type")

    cur = db.connection.cursor()
    cur.execute('UPDATE users SET type = %s WHERE id = %s', [type, user_id])
    db.connection.commit()
    cur.close()

    return '', 204


@app.route("/change_office", methods=["POST"])
@login_required
@admin_required
def change_office():
    """ Change office of user """
    user_id = request.form.get("user_id")
    office = request.form.get("office")

    cur = db.connection.cursor()
    cur.execute('UPDATE users SET office = %s WHERE id = %s', [office, user_id])
    db.connection.commit()
    cur.close()

    return '', 204


@app.route("/offices")
def offices():
    return render_template("offices.html")


if __name__ == '__main__':
    app.run(debug=True)
