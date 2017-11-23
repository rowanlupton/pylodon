from app import mongo
from config import API_ACCEPT_HEADERS
from .crypto import generate_keys

from activipy import vocab
from flask import abort, request, url_for
from flask_login import current_user
from httpsig import HeaderSigner, Signer
from httpsig.requests_auth import HTTPSignatureAuth
from webfinger import finger
from werkzeug.http import http_date, parse_date
import datetime, json, requests

context = [
            'https://www.w3.org/ns/activitystreams',
            {
              'manuallyApprovesFollowers': 'as:manuallyApprovesFollowers',
              'sensitive': 'as:sensitive'
              }
          ],

def return_new_user(handle, displayName, email, passwordHash):
  public, private = generate_keys()

  user =   {  
            'id': request.url_root+'api/'+handle, 
            '@context': context,
            'type': 'Person', 
            'username': handle,
            'acct': handle+'@'+request.host,
            'url': request.url_root+'@'+handle,
            'name': displayName, 
            'email': email, 
            'password': passwordHash,
            'manuallyApprovesFollowers': False,
            'avatar': None,
            'header': None,
            'following': request.url_root+'api/'+handle+'/following', 
            'followers': request.url_root+'api/'+handle+'/followers', 
            'liked': request.url_root+'api/'+handle+'/liked', 
            'inbox': request.url_root+'api/'+handle+'/inbox', 
            'outbox': request.url_root+'api/'+handle+'/feed',
            'metrics': {'post_count': 0},
            'created_at': get_time(),
            'publicKey': {
                          'id': request.url_root+'api/'+handle+'#main-key',
                          'owner': request.url_root+'api/'+handle,
                          'publicKeyPem': public
                          },
            'privateKey': private
          }


  return user
def find_user_or_404(handle):
  u = mongo.db.users.find_one({'username': handle})
  if not u:
    abort(404)
  else:
    return u
def get_logged_in_user():
  u = mongo.db.users.find_one({'id': current_user.get_id()})
  if not u:
    abort(404)
  else:
    return u


def get_time():

  return datetime.datetime.now().isoformat()
def createPost(content, handle, to, cc):
  u = find_user_or_404(handle)
  
  post_number = str(u['metrics']['post_count'])
  id = request.url_root+'api/'+u['username']+'/posts/'+post_number
  note_url = request.url_root+'@'+u['username']+'/'+post_number
  
  time = get_time()

  create =  {
            'id': id+'/activity',
            'type': 'Create',
            '@context': context,
            'actor': u['id'],
            'published': time,
            'to': to,
            'cc': cc,
            'object': {
                        'id': id,
                        'type': 'Note',
                        'summary': None,
                        'content': content,
                        'inReplyTo': None,
                        'published': time,
                        'url': note_url,
                        'attributedTo': u['id'],
                        'to': to,
                        'cc': cc,
                        'sensitive': False
                      },
            'signature': {
              'created': time,
              'creator': u['id']+'?get=main-key',
              'signatureValue': sign_object(u, content),
              'type': 'rsa-sha256'
            }
          }
  return json.dumps(create)
def createLike(actorAcct, post):
  to = post['attributedTo']
  if to in post:
    for t in post['to']:
      to.append(t)
  return vocab.Like(
                    context=context,
                    actor=actorAcct,
                    to=to,
                    object=post['id'])
def createFollow(actorAcct, otherUser):
  return vocab.Follow(
                      id=None,
                      context=context,
                      actor=actorAcct,
                      object=vocab.User(otherUser['id']))
def createAccept(followObj, to):
  acceptObj = {
                "@context": context,
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
  return rejectObj

# API
def check_accept_headers(request):
  if request.headers.get('accept'):
    if (request.headers['accept'] == 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"') or (request.headers['accept'] == "application/ld+json; profile='https://www.w3.org/ns/activitystreams'") or (request.headers['accept'] == 'application/activity+json'):
      return True
  return False
def check_content_headers(request):
  if request.headers.get('Content-Type'):
    if (request.headers['Content-Type'] == 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"') or (request.headers['Content-Type'] == "application/ld+json; profile='https://www.w3.org/ns/activitystreams'") or (request.headers['Content-Type'] == 'application/activity+json'):
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
  if addr.startswith('acct:'):
    addr = requests.get(get_address_from_webfinger(t), headers=sign_headers(u, API_ACCEPT_HEADERS)).json()
    
    return get_address_from_webfinger(addr)
  elif addr.startswith('http'):
    return addr

def get_address_from_webfinger(acct, box='inbox'):
  wf = finger(acct)
  user = wf.rel('self')
  u = requests.get(user, headers=API_ACCEPT_HEADERS).json()
  # address = u[box]

  return address
