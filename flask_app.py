import mysql.connector
from flask import Flask, render_template, session, redirect, request
from flask_mysqldb import MySQL
from flask_session import Session
from functools import wraps
from getpass import getpass

app = Flask(__name__)

app.config['MYSQL_DATABASE_USER'] = input("Enter username: ")
app.config['MYSQL_DATABASE_PASSWORD'] = getpass("Enter password: ")
app.config['MYSQL_DATABASE_DB'] = input("Enter database: ")
app.config['MYSQL_DATABASE_HOST'] = input("Enter host: ")

db = MySQL(app)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
@app.route('/')
def create_user():
    if request.method == "POST":
        username = request.form.get("username")
        usertype = request.form.get("usertype")

        cur = db.connection.cursor()
        cur.execute('INSERT INTO users (username, hash, type, blocked) VALUES (%s, "PASSWORD", %s, "false")', (username, usertype))
        db.connection.commit()
        cur.close()

        return render_template("/admin/admin-users.html")
    else:
        return render_template("/admin/admin-users.html")


if __name__ == '__main__':
    app.run(debug=True)
