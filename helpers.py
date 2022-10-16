from flask import Flask
from flask_mysqldb import MySQL

app = Flask(__name__)

# Create database
db = MySQL(app)


def history_get_dates(history):
    """ Gets last day, current day and next day for the navigation bar in the history function. """

    cur = db.connection.cursor()

    current_day = history[0]

    cur.execute("SELECT date FROM history WHERE date < %s GROUP BY date ORDER BY date DESC LIMIT 1",
                [history[0]])
    last_day_query = cur.fetchone()

    if last_day_query:
        last_day = last_day_query[0].strftime('%Y-%m-%d')
    else:
        last_day = history[0]

    cur.execute("SELECT date FROM history WHERE date > %s GROUP BY date ORDER BY date LIMIT 1",
                [history[0]])
    next_day_query = cur.fetchone()

    if next_day_query:
        next_day = next_day_query[0].strftime('%Y-%m-%d')
    else:
        next_day = history[0]

    cur.close()

    return current_day, last_day, next_day


def get_type(user_id):
    """ Get type of stored user id. """
    cur = db.connection.cursor()
    cur.execute('SELECT type FROM users WHERE id = %s', [user_id])
    type = cur.fetchone()
    return type[0]
