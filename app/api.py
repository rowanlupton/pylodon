# thanks to https://github.com/snarfed for the authorization -> signature headers hack

from app import mongo, rest_api
from config import API_ACCEPT_HEADERS, API_CONTENT_HEADERS
from .utilities import check_accept_headers, check_content_headers, createAccept, createFollow, createLike, createPost, createReject, find_user_or_404, get_address_from_webfinger, get_logged_in_user, get_time, sign_headers, sign_object

from activipy import vocab
from bson import ObjectId, json_util
from flask import abort, Blueprint, jsonify, make_response, redirect, request, Response, url_for
from flask_restful import Resource
from urllib.parse import unquote
from webfinger import finger

import json, requests

api = Blueprint('api', __name__, template_folder='templates')

class following(Resource):
  def get(self, handle):
    if True: #check_accept_headers(request):
      u = find_user_or_404(handle)

      if 'following_coll' in u:
        return u['following_coll']
      return []
    abort(406)

class followers(Resource):
  def get(self, handle):
    if True: #check_accept_headers(request):
      u = find_user_or_404(handle)

      if 'followers_coll' in u:
        return u['followers_coll']
      return []
    abort(406)

class liked(Resource):
  def get(self, handle):
    if check_accept_headers(request):
      u = find_user_or_404(handle)
      likes = []

      for post in mongo.db.posts.find({'object.liked_coll': u['id']}):
        likes.append(post['object'])

      return likes
    abort(406)

class inbox(Resource):
  def get(self, handle):
    if True: #check_accept_headers(request):
      items = list(mongo.db.posts.find({'to': get_logged_in_user()['id']}, {'_id': False}).sort('published', -1))

      return items
    abort(406)
  def post(self, handle):
    if True: #check_content_headers(request):
      u = find_user_or_404(handle)
      r = request.get_json()

      if r['type'] == 'Like':
        print('received Like')
        mongo.db.posts.update_one({'id': r['object']}, {'$push': {'object.liked_coll': r['actor']}}, upsert=True)

      elif r['type'] == 'Follow':
        print('received Follow')
        if r['actor'] in u['followers_coll']:
          return 400
        mongo.db.users.update_one({'id': u['id']}, {'$push': {'followers_coll': r['actor']}}, upsert=True)
        to = requests.get(r['object'], headers=sign_headers(u, API_ACCEPT_HEADERS)).json()['inbox']
        accept = createAccept(r, to)
        headers = sign_headers(u, API_CONTENT_HEADERS)

        requests.post(to, json=accept, headers=headers).json()
        return 202

      elif r['type'] == 'Accept':
        print('received Accept')
        mongo.db.users.update_one({'id': u['id']}, {'$push': {'following_coll': r['object']['actor']}}, upsert=True)
        return 202

      elif r['type'] == 'Create':
        print('received Create')
        print(r)
        if not mongo.db.posts.find({'id': r['id']}):
          mongo.db.posts.insert_one(r['object'].json())
          return 202

      else:
        print('other type')
      abort(400)
    abort(400)

class feed(Resource):
  def get(self, handle):
    if True: #check_accept_headers(request):
      u = find_user_or_404(handle)

      items = list(mongo.db.posts.find({'object.attributedTo': u['id']},{'_id': False}).sort('published', -1))
      context = ["https://www.w3.org/ns/activitystreams"]
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

      return Response(resp, headers=sign_headers(u, API_CONTENT_HEADERS))
    abort(406)

  def post(self, handle):
    if True: #check_content_headers(request):
      r = request.get_json()
      u = find_user_or_404(handle)
      to = []
      
      # if it's a note it turns it into a Create object
      if r['type'] == 'Note':
        print('Note')

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
          print('not a note')
          abort(403)

        print('Create')

        mongo.db.users.update({'acct': u['acct']}, {'$inc': {'metrics.post_count': 1}})

        content = r['object']['content']

        headers=sign_headers(u, API_CONTENT_HEADERS)

        if 'followers_coll' in u:
          for follower in u['followers_coll']:
            f = requests.get(follower, headers=sign_headers(u, API_ACCEPT_HEADERS)).json()
            to.append(f['inbox'])

        for t in r['to']:
          if t.startswith('acct:'):
            t = requests.get(get_address_from_webfinger(t), headers=sign_headers(u, API_ACCEPT_HEADERS)).json()
            to.append(t['inbox'])
        for cc in r['cc']:
          if cc.startswith('acct:'):
            to.append(get_address_from_webfinger(cc))

        mongo.db.posts.insert_one(r)

      if r['type'] == 'Like':
        if u['acct'] not in mongo.db.posts.find({'id': r['object']['id']})['likes']:
          mongo.db.posts.update({'id': r['object']['id']}, {'$push': {'likes': u['acct']}})

        if 'to' in r['object']:
          for t in r['object.to']:
            if t.startswith('acct:'):
              to.append(get_address_from_webfinger(t))
            else:
              to.append(t)
        if 'cc' in r['object']:
          for c in r['object.cc']:
            if c.startswith('acct:'):
              to.append(get_address_from_webfinger(c))
            else:
              to.append(c)

      if r['type'] == 'Follow':
        if r['object']['id'] not in u['following_coll']:
          followed_user = requests.get(r['object']['id']).json()

          to.append(followed_user['id'])

      if r['type'] == 'Update':
        ### update user object on other servers
        followers = u['followers_coll']

        for f in followers:
          to.append(f)

      if r['type'] == 'Delete':
        ### notify other servers that an object has been deleted
        followers = u['followers_coll']

        for f in followers:
          to.append(f)

      if r['type'] == 'Add':
        ### 
        pass

      if r['type'] == 'Remove':
        ### 
        pass

      if r['type'] == 'Announce':
        ### share
        pass

      if r['type'] == 'Block':
        ### 
        pass

      if r['type'] == 'Undo':
        ### 
        pass

      for t in to:
        requests.post(t, data=r, headers=sign_headers(u, API_CONTENT_HEADERS))
      return 202
    abort(400)

class user(Resource):
  def get(self, handle):
    # if check_accept_headers(request):
    u = find_user_or_404(handle)

    if request.args.get('get') == 'main-key':
      return u['publicKey']['publicKeyPem'].decode('utf-8')

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

    return user, sign_headers(u, API_CONTENT_HEADERS)
    abort(406)

# url handling
rest_api.add_resource(following, '/api/<string:handle>/following')
rest_api.add_resource(followers, '/api/<string:handle>/followers')
rest_api.add_resource(liked, '/api/<string:handle>/liked')
rest_api.add_resource(inbox, '/api/<string:handle>/inbox')
rest_api.add_resource(feed, '/api/<string:handle>/feed')
rest_api.add_resource(user, '/api/<string:handle>')