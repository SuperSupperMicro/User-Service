from flask import Blueprint, request, current_app
from datetime import datetime
import os
import pyodbc as db
from werkzeug.exceptions import HTTPException
from functools import wraps
from heftytoken import makeHeftyToken, decodeHeftyToken

from google.oauth2 import id_token
from google.auth.transport import requests

bp = Blueprint('users', __name__)

def makeToken(identifier):
    return makeHeftyToken(identifier, current_app.config['SECRET_KEY'])


def admin(function):
    @wraps(function)
    def wrapping_function(*args, **kwargs):
        # check if authorization header exists
        if not 'AUthorization' in request.headers:
            return AuthorizationRequired()

        # grab header data and get token
        hdata = request.headers['Authorization']
        hefty_token = str.replace(str(hdata), 'Bearer ', '')

        # retrieve data from token
        token_data = decodeHeftyToken(hefty_token)

        # grab token expiration from token_data
        token_expiration = token_data['exp']
        # convert string timestamp to datetime
        dt = datetime.strptime(token_expiration, '%Y-%m-%dT%H:%M:%SZ')

        # check if token has expired
        if not dt > datetime.utcnow():
            return AuthorizationRequired()

        # check if token was intended for this api
        sec = token_data['sec']
        if sec != current_app.config['SECRET_KEY']:
            return AuthorizationRequired()

        # get user id
        user_id = token_data['userID']

        try:
            # connect to db
            connection = _db_connect()
            cursor = connection.cursor()

            # execute stored procedure for checking user for admin user_role
            cursor.execute('{Call IsAdmin (?)}', (user_id))

            # get bool result
            val = cursor.fetchval()

            # commit any pending sql statements on this connection and close
            cursor.commit()
            cursor.close()
            del cursor
            connection.close()

            # check val for auth
            if val != 'TRUE':
                return AuthorizationRequired()

            return function(*args, **kwargs)

        except ValueError as e:
            print(e)
            return f"Error {e}"

    return wrapping_function





# MARK: - Routes
@bp.route('/')
def index():
    return "yes this is working, señor!"

@bp.post('/token_login')
def login():

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

        return {"token" : makeToken(userId)}

    except ValueError as e:
        print(e)
        return f"Error {e}"

@bp.route('/users/')
@admin
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
def update_user(user_id):
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




class AuthorizationRequired(HTTPException):
    code = 401
    description = 'Authorized users only'
