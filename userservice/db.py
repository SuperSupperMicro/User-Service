import pyodbc as db
import os

from flask import current_app, g

def db_connect():
    if 'con' not in g or 'cur' not in g:
        server = os.environ.get('MSSQL_ODBC_CONNECTION')
        database = os.environ.get('MSSQL_DATABASE')
        username = os.environ.get('MSSQL_DB_USERNAME')
        password = os.environ.get('MSSQL_DB_PASSWORD')

        try:
            g.con = db.connect(
                'DRIVER={ODBC Driver 17 for SQL Server};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s;TrustServerCertificate=yes'
                % (server, database, username, password)
            )
            g.cur = g.con.cursor()

            return g.cur

        except ValueError as e:
            print(e)
            return f"Error {e}"
    else:
        return g.cur


def db_close(e=None):
    connection = g.pop('con', None)
    cursor = g.pop('cur', None)

    if connection is not None:
        # commits all sql statements on this connection
        cursor.commit()
        # close & delete cursor
        cursor.close()
        del cursor
        # close connection
        connection.close()

def init_app(app):
    app.teardown_appcontext(db_close)