from flask import Blueprint, request, jsonify
from activipy import vocab
from app import mongo
from bson import ObjectId, json_util
import json

api = Blueprint('api', __name__, template_folder='templates')
API_HEADERS = {'Content-Type': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'}

@api.route('/api/<handle>/following')
def api_following(handle):
  feedObj = vocab.OrderedCollection(items=mongo.db.posts.find({'to': request.url_root+handle}).sort('_id', -1))
  if request.headers.get('Content-Type'):
    if (request.headers['Content-Type'] == 'application/ld+json' and request.headers['profile'] == 'https://www.w3.org/ns/activitystreams') or (request.headers['Content-Type'] == 'application/activity+json'):
      feedObj_sanitized = json.loads(json_util.dumps(feedObj.json()))
      return jsonify(feedObj_sanitized)
    else:
      pass
  else:
    pass

@api.route('/api/<handle>/followers')
def api_followers(handle):
  feedObj = vocab.OrderedCollection(items=mongo.db.posts.find({'to': request.url_root+handle}).sort('_id', -1))
  if request.headers.get('Content-Type'):
    if (request.headers['Content-Type'] == 'application/ld+json' and request.headers['profile'] == 'https://www.w3.org/ns/activitystreams') or (request.headers['Content-Type'] == 'application/activity+json'):
      feedObj_sanitized = json.loads(json_util.dumps(feedObj.json()))
      return jsonify(feedObj_sanitized)
    else:
      pass
  else:
    pass

@api.route('/api/<handle>/liked')
def api_liked(handle):
  feedObj = vocab.OrderedCollection(items=mongo.db.likes.find({'to': request.url_root+handle}).sort('_id', -1))
  if request.headers.get('Content-Type'):
    if (request.headers['Content-Type'] == 'application/ld+json' and request.headers['profile'] == 'https://www.w3.org/ns/activitystreams') or (request.headers['Content-Type'] == 'application/activity+json'):
      feedObj_sanitized = json.loads(json_util.dumps(feedObj.json()))
      return jsonify(feedObj_sanitized)
    else:
      pass
  else:
    pass

@api.route('/api/<handle>/inbox', methods=["GET", "POST"])
def api_inbox(handle):
  if request.method == 'POST':
    return '403'

    user = mongo.db.users.find_one({'id': SERVER_URL + handle})
    post = createPost(request.form['text'], user['name'], user['id'], user['inbox'])
    mongo.db.posts.insert_one(post.json())
    return redirect(request.args.get("next") or url_for('index'))
  elif request.method == 'GET':
    feedObj = vocab.OrderedCollection(items=mongo.db.posts.find({'to': request.url_root+handle}).sort('_id', -1))
    if request.headers.get('Content-Type'):
      if (request.headers['Content-Type'] == 'application/ld+json' and request.headers['profile'] == 'https://www.w3.org/ns/activitystreams') or (request.headers['Content-Type'] == 'application/activity+json'):
        feedObj_sanitized = json.loads(json_util.dumps(feedObj.json()))
        return jsonify(feedObj_sanitized)
      else:
        pass
    else:
      pass

def createPost(text, name, id, receivers):
  return vocab.Create(
                      actor=vocab.Person(
                            id,
                            displayName=name),
                      to=[receivers],
                      object=vocab.Note(
                                        content=text))

@api.route('/api/<handle>/feed', methods=["GET", "POST"])
def api_feed(handle):
  if request.method == 'POST':
    u = mongo.db.users.find_one({'id': SERVER_URL + handle})
    to = [u['outbox']]
    if request.data['to']:
      to.append(request.data['to'])

    post = createPost(request.data['text'], u['name'], u['id'], to)
    mongo.db.posts.insert_one(post.json())
    return redirect(request.args.get("next") or url_for('index'))

  elif request.method == 'GET':
    feedObj = vocab.OrderedCollection(items=mongo.db.posts.find({'to': request.url_root+handle+'/feed'}).sort('_id', -1))
    if request.headers.get('Content-Type'):
      if (request.headers['Content-Type'] == 'application/ld+json' and request.headers['profile'] == 'https://www.w3.org/ns/activitystreams') or (request.headers['Content-Type'] == 'application/activity+json'):
        feedObj_sanitized = json.loads(json_util.dumps(feedObj.json()))
        return jsonify(feedObj_sanitized)
      else:
        pass
    else:
      pass


