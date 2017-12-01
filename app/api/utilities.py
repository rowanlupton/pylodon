from app import mongo
from config import VALID_HEADERS, API_URI, ACCEPT_HEADERS, CONTENT_HEADERS

from flask import abort
from httpsig import HeaderSigner, Signer
from werkzeug.http import http_date
import datetime


def get_time():
    """
    """
    return datetime.datetime.now().isoformat()


def check_accept_headers(r):
    """
    """
    accept = r.headers.get('accept')
    if accept and (accept in VALID_HEADERS):
        return True
    return False


def check_content_headers(r):
    """
    """
    content_type = r.headers.get('Content-Type')
    if content_type and (content_type in VALID_HEADERS):
        return True
    return False


def check_headers(request):
    """
    checks whether the client has used the appropriate Accept or Content-Type headers in their request
    """
    method = request.method

    if method == 'GET':
        accept = request.headers.get('accept', None)
        if accept and (accept in VALID_HEADERS):
            pass
        else:
            abort(406) # Not Acceptable
    elif method == 'POST':
        content_type = request.headers.get('Content-Type', None)
        if content_type and (content_type in VALID_HEADERS):
            pass
        else:
            abort(415) # Unsupported Media Type
    else:
        abort(400) # Bad Request


def sign_headers(u, headers):
    """
    """
    key_id = u['publicKey']['@id']
    secret = u['privateKey']

    hs = HeaderSigner(key_id, secret, algorithm='rsa-sha256')
    auth = hs.sign({"Date": http_date()})

    auth['Signature'] = auth.pop('authorization')
    assert auth['Signature'].startswith('Signature ')
    auth['Signature'] = auth['Signature'][len('Signature '):]

    auth.update(headers)

    return auth


def content_headers(u):
    """
    """
    return sign_headers(u, CONTENT_HEADERS)


def accept_headers(u):
    """
    """
    return sign_headers(u, ACCEPT_HEADERS)


def sign_object(u, obj):
    """
    """
    # key_id = u['publicKey']['@id']
    secret = u['privateKey']

    hs = Signer(secret=secret, algorithm="rsa-sha256")
    auth_object = hs._sign(obj)

    return auth_object


def find_user(handle):
    """
    """
    u = mongo.db.users.find_one({'username': handle}, {'_id': False})
    if not u:
        print('user not found')
        return None
    return u


def find_post(handle, post_id):
    """
    """
    user_api_uri = API_URI+'/'+handle
    id = user_api_uri+'/'+post_id
    p = mongo.db.posts.find_one({'object.id': id}, {'_id': False})
    if not p:
        abort(404)
    return p
