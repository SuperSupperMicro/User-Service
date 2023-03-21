from flask import Blueprint, request
import os
import pyodbc as db

from google.oauth2 import id_token
from google.auth.transport import requests

bp = Blueprint('users', __name__)


@bp.route('/')
def index():
    return "yes this is working, señor!"


@bp.post('/token_sign_in')
def add_user():
    idToken = request.body['idToken']

    try:
        idinfo = id_token.verify_oauth2_token(idToken, requests.Request())
        print(idinfo)
        userid = idinfo['sub']
        print(userid)
        return userid

    except ValueError as e:
        print(e)
        return f"Error {e}"

@bp.route('/items/')
def inv_items():


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