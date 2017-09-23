from app import mongo

from activipy import vocab
from flask import request, abort, url_for
from flask_login import current_user
import datetime


def return_new_user(handle, displayName, email, passwordHash):
  return   {  
            'id': 'acct:'+handle+'@'+request.host, 
            '@context': 'https://www.w3.org/ns/activitystreams',
            'type': 'Person', 
            'username': handle,
            'acct': handle+'@'+request.host,
            'url': request.url_root+handle,
            'name': displayName, 
            'email': email, 
            'hashpw': passwordHash,
            'locked': False,
            'avatar': url_for('static', filename='img/defaultAvatar.png'),
            'header': url_for('static', filename='img/defaultHeader.gif'),
            'following': request.url_root+'api/'+handle+'/following', 
            'followers': request.url_root+'api/'+handle+'/followers', 
            'liked': request.url_root+'api/'+handle+'/liked', 
            'inbox': request.url_root+'api/'+handle+'/inbox', 
            'outbox': request.url_root+'api/'+handle+'/feed',
            'metrics': {'post_count': 0},
            'created_at': get_time()
          }
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
def createPost(text, name, acct, receivers):
  return vocab.Create(
                      context="https://www.w3.org/ns/activitystreams",
                      actor=vocab.Person(
                            acct+'@'+request.host,
                            displayName=name),
                      to=receivers,
                      object=vocab.Note(
                                        content=text),
                      created_at=get_time())
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

def accept_follow(actorAcct, followActivity):
  return vocab.Accept(
                      context="https://www.w3.org/ns/activitystreams",
                      actor=actorAcct,
                      object=followActivity)


# API
def check_accept_headers(request):
  print(request.headers)
  if request.headers.get('accept'):
    if (request.headers['accept'] == 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"') or (request.headers['Content-Type'] == 'application/activity+json'):
      return True
  return False

def check_content_headers