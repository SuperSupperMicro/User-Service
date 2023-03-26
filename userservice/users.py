from flask import Blueprint, request, g, abort
from userservice.db import db_connect
from userservice.auth import *

from google.oauth2 import id_token
from google.auth.transport import requests

bp = Blueprint('users', __name__)


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

    # verify token with google
    idinfo = id_token.verify_oauth2_token(idToken['idToken'], requests.Request())

    # check for required fields in json data
    if not 'sub' in idinfo or not 'name' in idinfo or not 'email' in idinfo:
        abort(502)

    # extract userinfo from google's response
    googleUserId = idinfo['sub']
    name = idinfo['name']
    email = idinfo['email']

    # create database cursor
    cursor = db_connect()

    # check if user exist IF NOT create user in database
    cursor.execute('{Call GoogleUserLogin (?,?,?)}', (googleUserId, name, email))

    # grab the user's user_id
    userId = cursor.fetchone()[0]

    return {"token": makeToken(str(userId))}

@bp.route('/users/')
@admin
def all_users():
    arr = []
    cursor = g.cur
    cursor.execute('EXEC GetAllUsers')

    row = cursor.fetchone()

    while row:
        arr.append(vars(User(row[0], row[1], row[2])))
        row = cursor.fetchone()

    return arr

@bp.route('/user/<int:user_id>')
@admin
def get_user_by_id(user_id):
    cursor = g.cur
    cursor.execute('{Call GetUserById (?)}', user_id)
    u = cursor.fetchone()
    ret = vars(User(u[0], u[1], u[2]))

    return ret

@bp.put('/user/<int:user_id>')
@admin
def update_user(user_id):
    json = request.json

    if not 'username' in json or not 'email' in json:
        abort(400)

    cursor = g.cur
    cursor.execute('{Call UpdateUser (?,?,?)}', (user_id, json['username'], json['email']))

    return "Success!", 200

@bp.delete('/user/<int:user_id>')
@admin
def soft_delete_user(user_id):
    cursor = g.cur
    cursor.execute('{Call SoftDeleteUser (?)}', user_id)

    return "Success!", 200

@bp.route('/user')
@admin
def get_current_user():
    cursor = g.cur
    user_id = get_user_from_token(request)
    cursor.execute('{Call GetUserById (?)}', user_id)
    val = cursor.fetchone()

    return vars(User(val[0], val[1], val[2]))

@bp.post('/add_role')
@admin
def add_user_role():
    json = request.json

    if not 'role_id' in json or not 'user_id' in json:
        abort(400)

    cursor = g.cur
    cursor.execute('{Call AddUserRole (?, ?)}', (json['user_id'], json['role_id']))

    return "Success", 201

class User:
    def __init__(self, id, username, email):
        self.user_id = id
        self.username = username
        self.email = email

    def __str__(self):
        return vars(self)