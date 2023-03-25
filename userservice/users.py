from flask import Blueprint, request, current_app, abort
from datetime import datetime
import os
import pyodbc as db
from werkzeug.exceptions import HTTPException
from functools import wraps
from heftytoken import makeHeftyToken, decodeHeftyToken

from google.oauth2 import id_token
from google.auth.transport import requests

bp = Blueprint('users', __name__)

# auth decorator
def admin(function):
    @wraps(function)
    def wrapping_function(*args, **kwargs):
        uid = get_user_from_token(request)
        try:
            # connect to db
            connection = _db_connect()
            cursor = connection.cursor()

            # execute stored procedure for checking user for admin user_role
            cursor.execute(f'EXEC IsAdmin {uid}')

            # get bool result
            val = cursor.fetchval()

            # # commit any pending sql statements on this connection and close
            _db_close(connection, cursor)

            # check val for auth
            if val != 'TRUE':
                return AuthorizationRequired()

            return function(*args, **kwargs)

        except ValueError as e:
            print(e)
            return f"Error {e}"

    return wrapping_function

"""
 MARK: - Routes
"""

@bp.route('/')
def index():
    return "See documentation for endpoint mapping!", 418

@bp.post('/token_login')
def login():
    # get token from request
    idToken = request.json

    try:
        # verify token with google
        idinfo = id_token.verify_oauth2_token(idToken['idToken'], requests.Request())

        # check for required fields in json data
        if not 'sub' in idinfo or not 'name' in idinfo or not 'email' in idinfo:
            abort(502)

        #extract userinfo from google's response
        googleUserId = idinfo['sub']
        name = idinfo['name']
        email = idinfo['email']

        # connect to the database
        connection = _db_connect()

        # create database cursor
        cursor = connection.cursor()

        # check if user exist IF NOT create user in database
        cursor.execute('{Call GoogleUserLogin (?,?,?)}', (googleUserId, name, email))

        # grab the user's user_id
        userId = cursor.fetchone()[0]
        # commit and close the cursor & connection
        _db_close(connection, cursor)

        return { "token" : makeToken(str(userId)) }

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
        cursor.execute('EXEC GetAllUsers')

        row = cursor.fetchone()

        while row:
            arr.append(vars(User(row[0], row[1], row[2])))
            row = cursor.fetchone()

        _db_close(connection, cursor)

        return arr

    except ValueError as e:
        print(e)
        return f"Error {e}"

@bp.route('/user/<int:user_id>')
@admin
def get_user_by_id(user_id):
    try:
        connection = _db_connect()
        cursor = connection.cursor()
        cursor.execute('{Call GetUserById (?)}', user_id)
        u = cursor.fetchone()
        ret = vars(User(u[0], u[1], u[2]))
        _db_close(connection, cursor)

        return ret

    except ValueError as e:
        print(e)
        return f"Error {e}"

@bp.put('/user/<int:user_id>')
@admin
def update_user(user_id):
    json = request.json

    if not 'username' in json or not 'email' in json:
        abort(400)

    try:
        connection = _db_connect()
        cursor = connection.cursor()
        cursor.execute('{Call UpdateUser (?,?,?)}', (user_id, json['username'], json['email']))
        _db_close(connection, cursor)

        return "Success!", 200

    except ValueError as e:
        print(e)
        return f"Error {e}"

@bp.delete('/user/<int:user_id>')
@admin
def soft_delete_user(user_id):
    try:
        connection = _db_connect()
        cursor = connection.cursor()
        cursor.execute('{Call SoftDeleteUser (?)}', user_id)
        _db_close(connection, cursor)

        return "Success!", 200

    except ValueError as e:
        print(e)
        return f"Error {e}"

@bp.route('/user')
@admin
def get_current_user():
    try:
        connection = _db_connect()
        cursor = connection.cursor()
        user_id = get_user_from_token(request)
        cursor.execute('{Call GetUserById (?)}', user_id)
        val = cursor.fetchone()
        _db_close(connection, cursor)

        return vars(User(val[0], val[1], val[2]))

    except ValueError as e:
        print(e)
        return f"Error {e}"

@bp.post('/add_role')
@admin
def add_user_role():
    json = request.json

    if not 'role_id' in json or not 'user_id' in json:
        abort(400)

    try:
        connection = _db_connect()
        cursor = connection.cursor()
        cursor.execute('{Call AddUserRole (?, ?)}', (json['user_id'], json['role_id']))
        _db_close(connection, cursor)

        return "Success", 201

    except ValueError as e:
        print(e)
        return f"Error {e}"


def _db_connect():
    server = os.environ.get('MSSQL_ODBC_CONNECTION')
    database = os.environ.get('MSSQL_DATABASE')
    username = os.environ.get('MSSQL_DB_USERNAME')
    password = os.environ.get('MSSQL_DB_PASSWORD')

    return db.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=%s;DATABASE=%s;UID=%s;PWD=%s;TrustServerCertificate=yes' % (server, database, username, password))


def _db_close(connection, cursor):
    # commits all sql statements on this connection
    cursor.commit()
    # close & delete cursor
    cursor.close()
    del cursor
    # close connection
    connection.close()


def makeToken(identifier):
    return makeHeftyToken(identifier, current_app.config['SECRET_KEY'])


def get_user_from_token(req):
    # check if authorization header exists
    if not 'AUthorization' in req.headers:
        return AuthorizationRequired()

    # grab header data and get token
    hdata = req.headers['Authorization']
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

    return int(token_data['userID'])


class AuthorizationRequired(HTTPException):
    code = 401
    description = 'Authorized users only'

class User:
    def __init__(self, id, username, email):
        self.user_id = id
        self.username = username
        self.email = email

    def __str__(self):
        return vars(self)