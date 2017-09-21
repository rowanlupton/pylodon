from app import mongo, rest_api
from config import API_HEADERS
from .utilities import find_user_or_404, get_logged_in_user, check_headers, createPost, get_time, follow_user, accept_follow

from flask import Blueprint, request, abort, redirect, url_for, jsonify
from flask_restful import Resource
from bson import ObjectId, json_util
import json, requests
from activipy import vocab
from webfinger import finger


api = Blueprint('api', __name__, template_folder='templates')

class following(Resource):
  def get(self, handle):
    if check_headers(request):
      u = find_user_or_404(handle)

      if 'following_coll' in u:
        following = u['following_coll']
        return following
      abort(404)
    abort(400)

class followers(Resource):
  def get(self, handle):
    if check_headers(request):
      u = find_user_or_404(handle)

      if 'followers_coll' in u:
        followers = u['followers_coll']
        return followers
      abort(404)
    abort(400)

class liked(Resource):
  def get(self, handle):
    if check_headers(request):
      u = find_user_or_404(handle)

      if 'likes' in u:
        likes = u['likes']
        return likes
      abort(404)
    abort(400)

class inbox(Resource):
  def get(self, handle):
    items = mongo.db.posts.find({'to': request.url_root+handle}).sort('_id', -1)
    feedObj = vocab.OrderedCollection(items=items)
    if check_headers(request):
      feedObj_sanitized = json.loads(json_util.dumps(feedObj.json()))
      return feedObj_sanitized
    else:
      abort(400)
  def post(self, handle):
    if check_headers(request):
      u = find_user_or_404(handle)
      r = request.get_json()

      if r['type'] == 'Like':
        mongo.db.posts.update_one({'@id': r['object']}, {'$push': {'likes': r['actor']}}, upsert=True)

      if r['type'] == 'Follow':
        mongo.db.users.update_one({'id': u['id']}, {'$push': {'followers_coll': r['actor']}}, upsert=True)
        a = requests.get(r['actor'], headers=API_HEADERS)
        print(a.content)
        # requests.post(a['inbox'], data=accept_follow(r), headers=API_HEADERS)

      if r['type'] == 'Accept':
        mongo.db.users.update_one({'id': u['id']}, {'$push': {'following_coll': r['actor']}}, upsert=True)

      if r['type'] == 'Create':
        if not mongo.db.posts.find({'_id': obj['_id']}):
          mongo.db.posts.insert_one(r['object'].json())

      return 202
    abort(400)

class feed(Resource):
  def get(self, handle):
    if check_headers(request):
      items = mongo.db.posts.find({'attributedTo': handle+'@'+request.host}).sort('created_at', -1)
      feedObj = vocab.OrderedCollection(items=items)
      feedObj_sanitized = json.loads(json_util.dumps(feedObj.json()))
      return feedObj
    else:
      abort(400)
  def post(self, handle):
    if check_headers(request):
      r = request.get_json()
      u = find_user_or_404(handle)
      
      # if it's a note it creates a request that will be handled by the next bit
      if r['@type'] == 'Note':
        obj = r
        r = vocab.Create(
          to=u['followers'],
          actor=u['acct'],
          object=obj)

      if r['@type'] == 'Create':
        if r['object']['@type'] != 'Note':
          abort(403)

        mongo.db.users.update({'acct': u['acct']}, {'$inc': {'metrics.post_count': 1}})
        id=request.url_root+u['username']+'/posts/'+str(mongo.db.users.find_one({'acct': u['acct']})['metrics']['post_count'])

        content = r['object']['content']
        note = vocab.Note(id=id, content=content, attributedTo=u['acct'], created_at=get_time())
        mongo.db.posts.insert_one(note.json())
        requests.post(r['to'], data=jsonify(r), headers=API_HEADERS)
        return redirect(request.args.get("next") or url_for('index'), 202)
      
      if r['@type'] == 'Like':
        if r['object']['@id'] not in mongo.db.users.find({'acct': r['actor']})['likes']:
          mongo.db.users.update({'acct': r['actor']}, {'$push': {'likes': r['object']['@id']}})
        if u['acct'] not in mongo.db.posts.find({'@id': r['object']['@id']})['likes']:
          mongo.db.posts.update({'@id': r['object']['@id']}, {'$push': {'likes': u['acct']}})


      if r['@type'] == 'Follow':
        pass
    abort(400)


class user(Resource):
  def get(self, handle):
    if check_headers(request):
      u = mongo.db.users.find({'username': handle})
      return json.loads(json_util.dumps(u))[0]
    abort(400)


# url handling
rest_api.add_resource(following, '/api/<string:handle>/following')
rest_api.add_resource(followers, '/api/<string:handle>/followers')
rest_api.add_resource(liked, '/api/<string:handle>/liked')
rest_api.add_resource(inbox, '/api/<string:handle>/inbox')
rest_api.add_resource(feed, '/api/<string:handle>/feed')
rest_api.add_resource(user, '/<string:handle>')