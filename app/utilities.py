from app import mongo

from activipy import vocab
from flask import request, abort

def find_user_or_404(handle):
  u = mongo.db.users.find_one({'id': request.url_root + handle})
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


# API utilities
def check_headers(request):
  print(request.headers)
  if request.headers.get('Content-Type'):
    if (request.headers['Content-Type'] == 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"') or (request.headers['Content-Type'] == 'application/activity+json'):
      print(request.headers)
      return True
    else:
      print(request.headers)
  print(request.headers)
  return False

def createPost(text, name, id, receivers):
  return vocab.Create(
                      actor=vocab.Person(
                            id,
                            displayName=name),
                      to=[receivers],
                      object=vocab.Note(
                                        content=text))