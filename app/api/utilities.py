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
def return_new_user(handle, displayName, email, passwordHash):
  public, private = generate_keys()

  user_uri = API_NAME+'/'+handle

  return  {  
            'id': user_uri, 
            '@context': DEFAULT_CONTEXT,
            'type': 'Person', 
            'username': handle,
            'acct': handle+'@'+server_name,
            'url': server_name+'@'+handle,
            'name': displayName, 
            'email': email, 
            'password': passwordHash,
            'manuallyApprovesFollowers': False,
            'avatar': None,
            'header': None,
            'following': user_uri+'/following', 
            'followers': user_uri+'/followers', 
            'liked': user_uri+'/liked', 
            'inbox': user_uri+'/inbox', 
            'outbox': user_uri+'/feed',
            'metrics': {'post_count': 0},
            'created_at': get_time(),
            'publicKey': {
                          'id': user_uri+'#main-key',
                          'owner': user_uri,
                          'publicKeyPem': public
                          },
            'privateKey': private
          }
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

def get_address_format(addr):
  if (addr.startswith('acct:') or
      addr.startswith('@') or
      addr == 'check for webfinger via regex'):
    addr = requests.get(get_address_from_webfinger(t), headers=sign_headers(u, API_ACCEPT_HEADERS)).json()
    
    return get_address_from_webfinger(addr)
  elif addr.startswith('http'):
    return addr

def get_address_from_webfinger(acct, box='inbox'):
  wf = finger(acct)
  user = wf.rel('self')
  u = requests.get(user, headers=API_ACCEPT_HEADERS).json()
  address = u[box]

  return user

def find_user_or_404(handle):
  u = mongo.db.users.find_one({'username': handle})
  if not u:
    print('user not found')
    abort(404)
  return u