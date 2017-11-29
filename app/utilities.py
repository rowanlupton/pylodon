from app import mongo
from config import API_ACCEPT_HEADERS, API_NAME, SERVER_NAME, VALID_HEADERS, DEFAULT_CONTEXT
from .crypto import generate_keys
from .api.utilities import find_user_or_404, get_time, sign_object

from activipy import vocab
from flask import abort, request, url_for
from flask_login import current_user
from httpsig import HeaderSigner, Signer
from httpsig.requests_auth import HTTPSignatureAuth
from webfinger import finger
from werkzeug.http import http_date, parse_date
import datetime, json, requests

def get_logged_in_user():
  u = mongo.db.users.find_one({'id': current_user.get_id()})
  if not u:
    abort(404)
  return u

def find_post_or_404(handle, post_id):
  id = request.url_root+'api/'+handle+'/'+post_id+'/activity'
  p = mongo.db.posts.find_one({'id': id}, {'_id': False})
  if not p:
    abort(404)
  return p

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

def get_address(addr, box='inbox'):
  try:
    if addr.startswith('@'):
      addr = 'acct:'+addr[1:]
  except AttributeError:
    for a in addr:
      if a.startswith('@'):
        addr = 'acct:'+addr[1:]
  try:    
    if addr.startswith('acct'):
      return get_address_from_webfinger(acct=addr, box=box)    
  except AttributeError:
    for a in addr:
      if addr.startswith('acct'):
        return get_address_from_webfinger(acct=a)
  
  try:
    if addr.startswith('http'):
      if addr is not 'https://www.w3.org/ns/activitystreams#Public':
        try:
          inbox = requests.get(addr, headers=sign_headers(get_logged_in_user(), API_ACCEPT_HEADERS)).json()['inbox']
          return inbox
        except AttributeError:
          return addr
      else:
        return addr
  except AttributeError:
    for a in addr:
      if addr.startswith('http'):
        if addr is not 'https://www.w3.org/ns/activitystreams#Public':
          try:
            inbox = requests.get(addr, headers=sign_headers(get_logged_in_user(), API_ACCEPT_HEADERS)).json()['inbox']
            return inbox
          except AttributeError:
            return addr
        else:
          return addr
      else:
        print('not a valid uri')
def get_address_from_webfinger(acct, box):
  wf = finger(acct)
  user = wf.rel('self')
  u = requests.get(user, headers=API_ACCEPT_HEADERS).json()
  address = u[box]

  return user

def create_post(content, handle, to, cc):
  u = find_user_or_404(handle)
  
  post_number = str(u['metrics']['post_count'])
  id = request.url_root+'api/'+u['username']+'/posts/'+post_number
  note_url = request.url_root+'@'+u['username']+'/'+post_number
  
  time = get_time()

  return vocab.Create(
                      id+'/activity',
                      actor=vocab.Person(
                        u['id'],
                        displayName=u['displayName']),
                      to=to,
                      cc=cc,
                      object=vocab.Note(
                        id,
                        url=note_url,
                        content=content)
                      )
def create_like(actorAcct, post):
  to = post['attributedTo']
  if posts.get('to'):
    for t in post['to']:
      to.append(t)
      
  return vocab.Like(
                    context=DEFAULT_CONTEXT,
                    actor=actorAcct,
                    to=to,
                    object=post['id'])
def create_follow(actorAcct, otherUser):
  return vocab.Follow(
                      id=None,
                      context=DEFAULT_CONTEXT,
                      actor=actorAcct,
                      object=vocab.User(otherUser['id']))
def create_accept(followObj, to):
  acceptObj = {
                "@context": DEFAULT_CONTEXT,
                'type': 'Accept',
                'to': to,
                'object': followObj
              }
  return acceptObj
def create_reject(followObj, to):
  rejectObj = {
                'type': 'Reject',
                'to': to,
                'object': followObj
              }
  return rejectObj