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

  user_api_uri = 'https://'+API_NAME+'/'+handle

  return  {  
            'id': user_api_uri, 
            '@context': DEFAULT_CONTEXT,
            'type': 'Person', 
            'username': handle,
            'acct': handle+'@'+SERVER_NAME,
            'url': 'https://'+SERVER_NAME+'/@'+handle,
            'name': displayName, 
            'email': email, 
            'password': passwordHash,
            'manuallyApprovesFollowers': False,
            'avatar': None,
            'header': None,
            'following': user_api_uri+'/following', 
            'followers': user_api_uri+'/followers', 
            'liked': user_api_uri+'/liked', 
            'inbox': user_api_uri+'/inbox', 
            'outbox': user_api_uri+'/feed',
            'metrics': {'post_count': 0},
            'created_at': get_time(),
            'publicKey': {
                          'id': user_api_uri+'#main-key',
                          'owner': user_api_uri,
                          'publicKeyPem': public
                          },
            'privateKey': private
          }
def check_accept_headers(request):
  if request.headers.get('accept'):
    accept = request.headers.get('accept').split(",")
    for h in VALID_HEADERS:
      if h in accept:
        return True
    return False
  return True
def check_content_headers(request):
  content_type = request.headers.get('content-type').split(",")
  for h in VALID_HEADERS:
    if h in content_type:
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
  u = mongo.db.users.find_one({'username': handle}, {'_id': False})
  if not u:
    print('user not found')
    abort(404)
  return u
def find_post_or_404(handle, post_id):
  id = 'https://'+API_NAME+'/'+handle+'/'+post_id+'/activity'
  p = mongo.db.posts.find_one({'id': id}, {'_id': False})
  if not p:
    abort(404)
  return p

def createPost(r, u):
  post_number = str(u['metrics']['post_count'])
  id = 'https://'+API_NAME+'/'+u['username']+'/'+post_number
  note_url = 'https://'+SERVER_NAME+'/@'+u['username']+'/'+post_number
  
  time = get_time()

  create =  {
            'id': id+'/activity',
            'type': 'Create',
            '@context': DEFAULT_CONTEXT,
            'actor': u['id'],
            'published': time,
            'to': r['to'],
            'bto': r['bto'],
            'cc': r['cc'],
            'bcc': r['bcc'],
            'audience': r['audience'],
            'inReplyTo': r['inReplyTo'],
            'object': {
                        'id': id,
                        'type': 'Note',
                        'summary': None,
                        'content': r['object'],
                        'inReplyTo': None,
                        'published': time,
                        'url': note_url,
                        'attributedTo': u['id'],
                        'to': r['to'],
                        'cc': r['cc'],
                        'sensitive': False
                      },
            'url': note_url+'/activity',
            'signature': {
              'created': time,
              'creator': u['id']+'?get=main-key',
              'signatureValue': sign_object(u, r['object']),
              'type': 'rsa-sha256'
            }
          }
  return json.dumps(create)
def createLike(actorAcct, post_id):
  to = post['attributedTo']
  if posts.get('to'):
    for t in post['to']:
      to.append(t)
      
  return vocab.Like(
                    context=DEFAULT_CONTEXT,
                    actor=actorAcct,
                    to=to,
                    object=post['id'])
def createFollow(actorAcct, otherUser):
  return vocab.Follow(
                      id=None,
                      context=DEFAULT_CONTEXT,
                      actor=actorAcct,
                      object=vocab.User(otherUser['id']))
def createAccept(followObj, to):
  acceptObj = {
                "@context": DEFAULT_CONTEXT,
                'type': 'Accept',
                'to': to,
                'object': followObj
              }
  return acceptObj
def createReject(followObj, to):
  rejectObj = {
                'type': 'Reject',
                'to': to,
                'object': followObj
              }
  return rejectOb