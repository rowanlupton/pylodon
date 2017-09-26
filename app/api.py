# thanks to https://github.com/snarfed for the authorization -> signature headers hack

from app import mongo, rest_api
from config import API_ACCEPT_HEADERS, API_CONTENT_HEADERS
from .utilities import check_accept_headers, check_content_headers, createAccept, createFollow, createLike, createPost, createReject, find_user_or_404, get_address_from_webfinger, get_logged_in_user, get_time, sign_headers, sign_object

from activipy import vocab
from bson import ObjectId, json_util
from flask import abort, Blueprint, jsonify, make_response, redirect, request, url_for
from flask_restful import Resource
from urllib.parse import unquote
from webfinger import finger

import json, requests

api = Blueprint('api', __name__, template_folder='templates')

class following(Resource):
  def get(self, handle):
    if check_accept_headers(request):
      u = find_user_or_404(handle)

      if 'following_coll' in u:
        following = u['following_coll']
        return following
      abort(404)
    pass

class followers(Resource):
  def get(self, handle):
    if check_accept_headers(request):
      u = find_user_or_404(handle)

      if 'followers_coll' in u:
        followers = u['followers_coll']
        return followers
      abort(404)
    pass

class liked(Resource):
  def get(self, handle):
    if check_accept_headers(request):
      u = find_user_or_404(handle)

      if 'likes' in u:
        likes = u['likes']
        return likes
      abort(404)
    pass

class inbox(Resource):
  def get(self, handle):
    
    feedObj = vocab.OrderedCollection(items=items)
    if check_accept_headers(request):
      items = list(mongo.db.posts.find({'to': get_logged_in_user()['id']}, {'_id': False}).sort('published', -1))

      return items
    else:
      pass
  def post(self, handle):
    if check_content_headers(request):
      u = find_user_or_404(handle)
      print(u)
      print(handle)
      r = request.get_json()

      if r['type'] == 'Like':
        mongo.db.posts.update_one({'id': r['object']}, {'$push': {'likes': r['actor']}}, upsert=True)

      if r['type'] == 'Follow':
        mongo.db.users.update_one({'id': u['id']}, {'$push': {'followers_coll': r['actor']}}, upsert=True)
        accept = createAccept(r)
        requests.post(accept['to'], data=accept, headers=API_CONTENT_HEADERS)

      if r['type'] == 'Accept':
        mongo.db.users.update_one({'id': u['id']}, {'$push': {'following_coll': r['actor']}}, upsert=True)

      if r['type'] == 'Create':
        if not mongo.db.posts.find({'_id': r['_id']}):
          mongo.db.posts.insert_one(r['object'].json())

      return 202
    abort(400)

class feed(Resource):
  def get(self, handle):
    # if check_accept_headers(request):
    u = find_user_or_404(handle)

    items = list(mongo.db.posts.find({'object.attributedTo': u['acct']},{'_id': False}).sort('published', -1))
    context = vocab.OrderedCollection().types_expanded
    context.append( {
                      'manuallyApprovesFollowers': 'as:manuallyApprovesFollowers',
                      'sensitive': 'as:sensitive'
                    })
    resp =  {
              '@context': context,
              'id': u['outbox'],
              'type': 'OrderedCollection',
              'totalItems': len(items),
              'orderedItems': items
            }

    return resp, sign_headers(u)
    # else:
    #   return redirect(unquote(url_for('viewFeed', handle=handle)))
  def post(self, handle):
    if check_content_headers(request):
      r = request.get_json()
      u = find_user_or_404(handle)
      
      # if it's a note it creates a request that will be handled by the next bit
      if r['type'] == 'Note':
        to = []
        if 'to' in r:
          for t in r['to']:
            if t.startswith('acct:'):
              t = get_address_from_webfinger(t)
            to.append(t)
        cc = []
        if 'cc' in r:
          for c in r['cc']:
            if c.startswith('acct:'):
              c = get_address_from_webfinger(c)
            cc.append(c)

        obj = r
        r = {
              'id': obj['id']+'/activity',
              'type': 'Create',
              'actor': u[id],
              'published': obj['published'],
              'to': to,
              'cc': cc,
              'object': obj.get_json()
            }

      if r['type'] == 'Create':
        if r['object']['type'] != 'Note':
          abort(403)

        mongo.db.users.update({'acct': u['acct']}, {'$inc': {'metrics.post_count': 1}})

        content = r['object']['content']

        headers=API_CONTENT_HEADERS.update(sign_headers(u))

        for to in r['to']:
          if to.startswith('acct:'):
            to = get_address_from_webfinger(to)
          requests.post(to, data=r, headers=headers)
        for cc in r['cc']:
          if cc.startswith('acct:'):
            cc = get_address_from_webfinger(cc)
          requests.post(cc, data=r, headers=headers)

        mongo.db.posts.insert_one(r)

        return 202
      


      if r['type'] == 'Like':
        if r['object']['@id'] not in mongo.db.users.find({'acct': r['actor']})['likes']:
          mongo.db.users.update({'acct': r['actor']}, {'$push': {'likes': r['object']['@id']}})
        if u['acct'] not in mongo.db.posts.find({'@id': r['object']['@id']})['likes']:
          mongo.db.posts.update({'@id': r['object']['@id']}, {'$push': {'likes': u['acct']}})


      if r['type'] == 'Follow':
        pass
    abort(400)

class user(Resource):
  def get(self, handle):
    print('user-get')
    # if check_accept_headers(request):
    print('right headers')
    u = find_user_or_404(handle)

    user =  {
             '@context': u['@context'],
             'id': u['id'],
             'followers': u['followers'],
             'following': u['following'],
             'icon': {'type': 'Image', 'url': u['avatar']},
             'inbox': u['inbox'],
             'manuallyApprovesFollowers': u['manuallyApprovesFollowers'],
             'name': u['name'],
             'outbox': u['outbox'],
             'preferredUsername': u['username'],
             'publicKey': {'id': u['id']+'#main-key', 'owner': u['id'], 'publicKeyPem': u['publicKey']['publicKeyPem'].decode('utf-8')},
             'summary': '',
             'type': u['type'],
             'url': u['url']
            }

    return user, sign_headers(u)
    redirect(unquote(url_for('viewFeed', handle=handle)))

# url handling
rest_api.add_resource(following, '/api/<string:handle>/following')
rest_api.add_resource(followers, '/api/<string:handle>/followers')
rest_api.add_resource(liked, '/api/<string:handle>/liked')
rest_api.add_resource(inbox, '/api/<string:handle>/inbox')
rest_api.add_resource(feed, '/api/<string:handle>/feed')
rest_api.add_resource(user, '/api/<string:handle>')