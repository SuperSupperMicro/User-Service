from flask import request, g, current_app, abort
from datetime import datetime
from werkzeug.exceptions import HTTPException, Unauthorized
from functools import wraps
from userservice.db import db_connect
from heftytoken import makeHeftyToken, decodeHeftyToken


# auth decorator
def admin(function):
    @wraps(function)
    def wrapping_function(*args, **kwargs):
        try:
            uid = get_user_from_token(request)
        except HTTPException as e:
            return f"{e}", 401

        # save the user_id
        g.uid = uid

        # connect to dbx
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
    if not 'Authorization' in req.headers:
        raise Unauthorized(auth_error + 'No Authorization headers', 401)

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
        raise Unauthorized(auth_error + 'Token has expired!', 401)

    # check if token was intended for this api
    sec = token_data['sec']
    if sec != current_app.config['SECRET_KEY']:
        raise Unauthorized(auth_error + 'Token was unable to be verified for use with this application', 401)

    return int(token_data['userID'])

auth_error = 'Authorization required! \n'

class AuthorizationRequired(Unauthorized):
    code = 401
    description = 'Authorized admins only'