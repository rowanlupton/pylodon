from app import mongo, rest_api
from .utilities import find_user_or_404, get_logged_in_user, check_headers, createPost

from flask import Blueprint, request, abort
from flask_restful import Resource
from bson import ObjectId, json_util
import json


api = Blueprint('api', __name__, template_folder='templates')

class following(Resource):
  def get(self, handle):
    feedObj = vocab.OrderedCollection(items=mongo.db.posts.find({'to': request.url_root+handle}).sort('_id', -1))
    if check_headers():
      feedObj_sanitized = json.loads(json_util.dumps(feedObj.json()))
      return feedObj_sanitized
    else:
      abort(400)

class followers(Resource):
  def get(self, handle):
    feedObj = vocab.OrderedCollection(items=mongo.db.posts.find({'to': request.url_root+handle}).sort('_id', -1))
    if check_headers():
      feedObj_sanitized = json.loads(json_util.dumps(feedObj.json()))
      return feedObj_sanitized
    else:
      abort(400)

class liked(Resource):
  def get(self, handle):
    feedObj = vocab.OrderedCollection(items=mongo.db.likes.find({'to': request.url_root+handle}).sort('_id', -1))
    if check_headers():
      feedObj_sanitized = json.loads(json_util.dumps(feedObj.json()))
      return feedObj_sanitized
    else:
      abort(400)

class inbox(Resource):
  def get(self, handle):
    feedObj = vocab.OrderedCollection(items=mongo.db.posts.find({'to': request.url_root+handle}).sort('_id', -1))
    if check_headers(request):
      feedObj_sanitized = json.loads(json_util.dumps(feedObj.json()))
      return feedObj_sanitized
    else:
      abort(400)
  def post(self, handle):
    abort(403)

    user = mongo.db.users.find_one({'id': SERVER_URL + handle})
    post = createPost(request.form['text'], user['name'], user['id'], user['inbox'])
    mongo.db.posts.insert_one(post.json())
    return redirect(request.args.get("next") or url_for('index'))

class feed(Resource):
  def get(self, handle):
    if check_headers(request):
      items = mongo.db.posts.find({'to': request.url_root+handle+'/feed'}).sort('_id', -1)
      feedObj = vocab.OrderedCollection(items=items)
      feedObj_sanitized = json.loads(json_util.dumps(feedObj.json()))
      return feedObj_sanitized
    else:
      abort(400)
  def post(self, handle):
    u = find_user_or_404(handle)

    to = [u.outbox]
    if request.data['to']:
      to.append(request.data['to'])

    post = createPost(request.data['text'], u['name'], u['id'], to)
    mongo.db.posts.insert_one(post.json())
    return redirect(request.args.get("next") or url_for('index'))


# url handling
rest_api.add_resource(following, '/api/<string:handle>/following')
rest_api.add_resource(followers, '/api/<string:handle>/followers')
rest_api.add_resource(liked, '/api/<string:handle>/liked')
rest_api.add_resource(inbox, '/api/<string:handle>/inbox')
rest_api.add_resource(feed, '/api/<string:handle>/feed')