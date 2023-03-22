from flask import Blueprint, request
import os
import pyodbc as db

from google.oauth2 import id_token
from google.auth.transport import requests

bp = Blueprint('users', __name__)

# MARK: - Routes
@bp.route('/')
def index():
    return "yes this is working, señor!"


@bp.post('/token_sign_in')
def add_user():

    # get token from request
    idToken = request.json

    try:
        # verify token with google
        idinfo = id_token.verify_oauth2_token(idToken['idToken'], requests.Request())

        #extract userinfo from google's response
        googleUserId = idinfo['sub']
        name = idinfo['name']
        email = idinfo['email']

        # connect to the database
        connection = _db_connect()

        # create database cursor
        cursor = connection.cursor()

        # check if user exist IF NOT create user in database
        storedProcedure = f"""
        IF NOT EXISTS (Select 1 FROM dbo.users where google_id='{googleUserId}')
            BEGIN
                EXEC CreateNewGoogleUser @Username='{name}', @GID='{googleUserId}', @Email='{email}';
            END;
        """

        cursor.execute(storedProcedure)

        # query database for new user_id
        cursor.execute('EXEC GetUserByGID @GID=?', googleUserId)

        # return user_id
        userId = str(cursor.fetchval())

        # commits all sql statements on this connection
        cursor.commit()

        # close connection & delete cursor
        cursor.close()
        del cursor
        connection.close()

        return userId

    except ValueError as e:
        print(e)
        return f"Error {e}"



@bp.route('/users/')
def all_users():
    arr = []
    try:
        connection = _db_connect()
        cursor = connection.cursor()
        cursor.execute("SELECT user_id, username, email  FROM dbo.users WHERE active='TRUE'")

        row = cursor.fetchone()

        while row:
            arr.append({
                "id": row[0],
                "username": row[1],
                "email": row[2]
            })
            row = cursor.fetchone()

        cursor.close()
        del cursor
        connection.close()

        return arr

    except ValueError as e:
        print(e)
        return f"Error {e}"


@bp.route('/user/<int:user_id>')
def get_user_by_id(user_id):
    try:
        connection = _db_connect()
        cursor = connection.cursor()

        cursor.execute(f'SELECT TOP 1 user_id, username, email FROM dbo.users WHERE user_id = {user_id}')
        u = cursor.fetchone()

        ret = {
            "id": u[0],
            "username": u[1],
            "email": u[2]
        }

        cursor.close()
        del cursor
        connection.close()

        return ret

    except ValueError as e:
        print(e)
        return f"Error {e}"

@bp.put('/user/<int:user_id>')
def updateUser(user_id):
    json = request.json

    try:
        connection = _db_connect()
        cursor = connection.cursor()

        cursor.execute('{Call UpdateUser (?,?,?)}', (user_id, json['username'], json['email']))

        cursor.commit()

        cursor.close()
        del cursor
        connection.close()

        return "Success!"

    except ValueError as e:
        print(e)
        return f"Error {e}"

@bp.delete('/user/<int:user_id>')
def soft_delete_user(user_id):
    try:
        connection = _db_connect()
        cursor = connection.cursor()

        cursor.execute(f'UPDATE dbo.users SET active = FALSE WHERE user_id = {user_id}')

        cursor.commit()

        cursor.close()
        del cursor
        connection.close()

        return "Success!"

    except ValueError as e:
        print(e)
        return f"Error {e}"

def _db_connect():
    server = os.environ.get('MSSQL_ODBC_CONNECTION')
    database = os.environ.get('MSSQL_DATABASE')
    username = os.environ.get('MSSQL_DB_USERNAME')
    password = os.environ.get('MSSQL_DB_PASSWORD')

    return db.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s;TrustServerCertificate=yes' % (server, database, username, password))