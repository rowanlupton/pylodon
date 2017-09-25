from app import mongo
from config import API_ACCEPT_HEADERS
from .crypto import generate_keys

from activipy import vocab
from flask import request, abort, url_for
from flask_login import current_user
from httpsig import HeaderSigner, Signer
from httpsig.requests_auth import HTTPSignatureAuth
from webfinger import finger
from werkzeug.http import http_date, parse_date
import datetime, json, requests


def return_new_user(handle, displayName, email, passwordHash):
  public, private = generate_keys()

  user =   {  
            'id': request.host+'api/'+handle, 
            '@context': [
                          'https://www.w3.org/ns/activitystreams',
                          {'manuallyApprovesFollowers': 'as:manuallyApprovesFollowers'}
                        ],
            'type': 'Person', 
            'username': handle,
            'acct': handle+'@'+request.host,
            'url': request.url_root+'users/'+handle,
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
  id = request.url_root+u['username']+'/posts/'+post_number
  note_url = request.url_root+'@'+post_number
  
  time = get_time()

  create =  {
            'id': id+'/activity',
            'type': 'Create',
            'context': vocab.Create().types_expanded,
            'actor': u['acct'],
            'published': time,
            'to': to,
            'cc': cc,
            'object': {
                        'id': id,
                        'type': 'Note',
                        'summary': None,
                        'content': content,
                        'published': time,
                        'url': note_url,
                        'attributedTo': u['acct'],
                        'to': to,
                        'cc': cc
                      }
          }
  return json.dumps(create)
def createLike(actorAcct, post):
  to = post['attributedTo']
  if to in post:
    for t in post['to']:
      to.append(t)
  return vocab.Like(
                    context="https://www.w3.org/ns/activitystreams",
                    actor=actorAcct,
                    to=to,
                    object=vocab.Note(
                                      context={"@language": 'en'},
                                      id=post['@id'],
                                      attributedTo=post['attributedTo'],
                                      content=post['content']))
def follow_user(actorAcct, otherUser):
  return vocab.Follow(
                      context="https://www.w3.org/ns/activitystreams",
                      actor=actorAcct,
                      object=vocab.User(
                                        context={"@language": 'en'},
                                        id=otherUser['id']))


# API
def check_accept_headers(request):
  if request.headers.get('accept'):
    if (request.headers['accept'] == 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"') or (request.headers['accept'] == 'application/activity+json'):
      return True
  return False
def check_content_headers(request):
  if request.headers.get('Content-Type'):
    if (request.headers['Content-Type'] == 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"') or (request.headers['Content-Type'] == 'application/activity+json'):
      return True
  return False
def sign_headers(u):
  key_id = u['publicKey']['id']
  secret = u['privateKey']

  hs = HeaderSigner(key_id, secret, algorithm='rsa-sha256')
  auth = hs.sign({"Date": http_date()})

  auth['Signature'] = auth.pop('authorization')
  assert auth['Signature'].startswith('Signature ')
  auth['Signature'] = auth['Signature'][len('Signature '):]

  return auth
def sign_object(u, r):
  key_id = u['publicKey']['id']
  secret = u['privateKey']

  hs = Signer(secret=secret, algorithm="rsa-sha256")
  auth_object = hs._sign(r.json())

  return auth_object
def get_address_from_webfinger(acct, box='inbox'):
  wf = finger(acct)
  user = wf.rel('self')
  u = requests.get(user, headers=API_ACCEPT_HEADERS).json()
  address = u[box]

  return address