from flask import request, g, current_app
from datetime import datetime
from werkzeug.exceptions import HTTPException
from functools import wraps
from userservice.db import db_connect
from heftytoken import makeHeftyToken, decodeHeftyToken


# auth decorator
def admin(function):
    @wraps(function)
    def wrapping_function(*args, **kwargs):
        uid = get_user_from_token(request)

        # connect to db
        cursor = db_connect()

        # execute stored procedure for checking user for admin user_role
        cursor.execute(f'EXEC IsAdmin {uid}')

        # get bool result
        val = cursor.fetchval()

        # check val for auth
        if val != 'TRUE':
            return AuthorizationRequired()

        return function(*args, **kwargs)

    return wrapping_function

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