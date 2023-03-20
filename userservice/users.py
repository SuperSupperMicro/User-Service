from flask import (
Blueprint, flash, g, redirect, render_template, request, session, url_for
)
import os

bp = Blueprint('users', __name__)


@bp.route('/')
def index():
    return "yes this is working, señor!"

@bp.route('/items')
def invItems():
    import pyodbc as db

    server = os.environ.get('MSSQL_ODBC_CONNECTION')
    database = os.environ.get('MSSQL_DATABASE')
    username = os.environ.get('MSSQL_DB_USERNAME')
    password = os.environ.get('MSSQL_DB_PASSWORD')

    arr = []

    try:
        connection = db.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s;TrustServerCertificate=yes' % (server, database, username, password))

        cursor = connection.cursor()

        cursor.execute('SELECT *  FROM dbo.inventory_items')

        row = cursor.fetchone()
        while row:
            print(row)
            arr.append(str(row))
            row = cursor.fetchone()

        cursor.close()
        del cursor

        connection.close()

    except Exception as e:
        print(e)

    return arr