from app import mongo
from config import API_ACCEPT_HEADERS, API_NAME, SERVER_NAME, VALID_HEADERS, DEFAULT_CONTEXT
from ..crypto import generate_keys

from flask import abort, request
from httpsig import HeaderSigner, Signer
from webfinger import finger
from werkzeug.http import http_date
import datetime, requests

def get_time():

  return datetime.datetime.now().isoformat()
def get_logged_in_user():
  u = mongo.db.users.find_one({'id': current_user.get_id()})
  if not u:
    abort(404)
  return u

def check_accept_headers(request):
  accept = request.headers.get('accept')
  if accept and (accept in VALID_HEADERS):
    return True
  return False
def check_content_headers(request):
  content_type = request.headers.get('Content-Type')
  if content_type and (content_type in VALID_HEADERS):
    return True
  return False
def sign_headers(u, headers):
  key_id = u['publicKey']['id']
  secret = u['privateKey']

  hs = HeaderSigner(key_id, secret, algorithm='rsa-sha256')
  auth = hs.sign({"Date": http_date()})

  auth['Signature'] = auth.pop('authorization')
  assert auth['Signature'].startswith('Signature ')
  auth['Signature'] = auth['Signature'][len('Signature '):]

  auth.update(headers)

  return auth
def sign_object(u, obj):
  key_id = u['publicKey']['id']
  secret = u['privateKey']

  hs = Signer(secret=secret, algorithm="rsa-sha256")
  auth_object = hs._sign(obj)

  return auth_object

def find_user_or_404(handle):
  u = mongo.db.users.find_one({'username': handle})
  if not u:
    print('user not found')
    abort(404)
  return u