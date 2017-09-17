from app import mongo

from activipy import vocab
from flask import request, abort, url_for
from flask_login import current_user
import datetime

def return_new_user(handle, displayName, email, passwordHash):
  now = datetime.datetime.now()

  return   {  
            'id': 'acct:'+handle+'@'+request.host, 
            'context': 'https://www.w3.org/ns/activitystreams',
            'type': 'Person', 
            'username': handle,
            'acct': handle,
            'url': request.url_root+handle,
            'name': displayName, 
            'email': email, 
            'password': passwordHash,
            'locked': False,
            'avatar': url_for('static', filename='img/defaultAvatar.png'),
            'header': url_for('static', filename='img/defaultHeader.gif'),
            'following': request.url_root+'api/'+handle+'/following', 
            'followers': request.url_root+'api/'+handle+'/followers', 
            'liked': request.url_root+'api/'+handle+'/liked', 
            'inbox': request.url_root+'api/'+handle+'/inbox', 
            'outbox': request.url_root+'api/'+handle+'/feed',
            'created_at': now.isoformat()
          }
def find_user_or_404(handle):
  u = mongo.db.users.find_one({'username': handle})
  if not u:
    abort(404)
  else:
    return u
def get_logged_in_user():
  u = mongo.db.users.find_one({'acct': current_user.get_id()})
  if not u:
    abort(404)
  else:
    return u


# API utilities
def check_headers(request):
  print(request.headers)
  if request.headers.get('Content-Type'):
    if (request.headers['Content-Type'] == 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"') or (request.headers['Content-Type'] == 'application/activity+json'):
      return True
  return False

def createPost(text, name, acct, receivers):
  now = datetime.datetime.now()
  return vocab.Create(
                      actor=vocab.Person(
                            acct+'@'+request.host,
                            displayName=name),
                      to=receivers,
                      object=vocab.Note(
                                        content=text),
                      created_at=now.isoformat())