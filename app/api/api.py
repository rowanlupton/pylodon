# thanks to https://github.com/snarfed for the authorization -> signature headers hack

from app import mongo, rest_api
from config import API_ACCEPT_HEADERS, API_CONTENT_HEADERS
from .utilities import check_accept_headers, check_content_headers, find_user_or_404, get_time, sign_headers, sign_object

from activipy import vocab
from bson import ObjectId, json_util
from flask import abort, Blueprint, jsonify, make_response, redirect, request, Response, url_for
from flask_restful import Resource
from urllib.parse import unquote
from webfinger import finger

import json, requests

api = Blueprint('api', __name__, template_folder='templates')
print('registered api')

class following(Resource):
  def get(self, handle):
    if check_accept_headers(request):
      u = find_user_or_404(handle)

      return u.get('following_coll', [])
    abort(406)

class followers(Resource):
  def get(self, handle):
    print('followers get')
    if check_accept_headers(request):
      u = find_user_or_404(handle)

      return u.get('followers_coll', [])
    abort(406)

class liked(Resource):
  def get(self, handle):
    if check_accept_headers(request):
      u = find_user_or_404(handle)
      likes = []

      for post in mongo.db.posts.find({'object.liked_coll': u['@id']}):
        likes.append(post['object'])

      return likes
    abort(406)

class inbox(Resource):
  def get(self, handle):
    print('inbox get')
    if check_accept_headers(request):
      items = list(mongo.db.posts.find({'to': find_user_or_404(handle)['@id']}, {'_id': False}).sort('published', -1))

      return items
    abort(406)
  def post(self, handle):
    print('inbox post')
    if check_content_headers(request):
      u = find_user_or_404(handle)
      r = request.get_json()

      if r['type'] == 'Like':
        print('received Like')
        mongo.db.posts.update_one({'id': r['object']}, {'$push': {'object.liked_coll': r['actor']}}, upsert=True)

      elif r['type'] == 'Follow':
        if u.get('followers_coll'):
          if u['followers_coll'].get('actor'):
            return 400

        mongo.db.users.update_one({'id': u['@id']}, {'$push': {'followers_coll': r['actor']}}, upsert=True)
        to = requests.get(r['actor'], headers=sign_headers(u, API_ACCEPT_HEADERS)).json()['inbox']
        accept = createAccept(r, to)
        headers = sign_headers(u, API_CONTENT_HEADERS)

        requests.post(to, json=accept, headers=headers)
        return 202

      elif r['type'] == 'Accept':
        print('received Accept')
        mongo.db.users.update_one({'id': u['@id']}, {'$push': {'following_coll': r['object']['actor']}}, upsert=True)
        return 202

      elif r['type'] == 'Create':
        # this needs more stuff, like creating a user if necessary
        print('received Create')
        print(r)
        if not mongo.db.posts.find({'id': r['@id']}):
          mongo.db.posts.insert_one(r['object'].json())
          return 202

      else:
        print('other type')
        print(r)
      abort(400)
    abort(400)

class feed(Resource):
  def get(self, handle):
    print('feed get')
    if check_accept_headers(request):
      u = find_user_or_404(handle)

      items = list(mongo.db.posts.find({'object.attributedTo': u['@id']},{'_id': False}).sort('published', -1))
      resp =  {
                '@context': DEFAULT_CONTEXT,
                '@id': u['outbox'],
                '@type': 'OrderedCollection',
                'totalItems': len(items),
                'orderedItems': items
              }

      return Response(json.dumps(resp), headers=sign_headers(u, API_CONTENT_HEADERS))
    abort(406)

  def post(self, handle):
    if check_content_headers(request):
      r = request.get_json()
      u = find_user_or_404(handle)
      
      # if it's a note it turns it into a Create object
      if r['@type'] == 'Note':
        print('Note')

        obj = r
        r = {
              'id': obj['@id']+'/activity',
              'type': 'Create',
              'actor': u[id],
              'published': obj['published'],
              'to': to,
              'cc': cc,
              'object': obj.get_json()
            }

      if r['@type'] == 'Create':
        if r['object']['@type'] != 'Note':
          print(str(r))
          print('not a note')
          abort(403)

        print('Create')

        mongo.db.users.update({'acct': u['acct']}, {'$inc': {'metrics.post_count': 1}})

        content = r['object']['content']

        if u.get('followers_coll'):
          for follower in u['followers_coll']:
            to.append(follower)

        mongo.db.posts.insert_one(r)
        # remove the _id object that pymongo added because it screws up later
        r.pop('_id')

      elif r['@type'] == 'Like':
        if u['acct'] not in mongo.db.posts.find({'@id': r['object']['@id']})['likes']:
          mongo.db.posts.update({'@id': r['object']['@id']}, {'$push': {'likes': u['acct']}})

      elif r['@type'] == 'Follow':
        if r['object']['@id'] not in u['following_coll']:
          followed_user = requests.get(r['object']['@id']).json()

          to.append(followed_user['@id'])

      elif r['@type'] == 'Update':
        ### update user object on other servers
        followers = u['followers_coll']

        for f in followers:
          to.append(f)

      elif r['@type'] == 'Delete':
        ### notify other servers that an object has been deleted
        followers = u['followers_coll']

        for f in followers:
          to.append(f)

      elif r['@type'] == 'Add':
        ### 
        pass

      elif r['@type'] == 'Remove':
        ### 
        pass

      elif r['@type'] == 'Announce':
        ### share
        pass

      elif r['@type'] == 'Block':
        ### 
        pass

      elif r['@type'] == 'Undo':
        ### 
        pass

      for t in to:
        user = requests.get(t, headers=sign_headers(u, API_ACCEPT_HEADERS)).json()
        if user.get('inbox'):
          inbox = user['inbox']
        else:
          inbox = t
        print('to: '+inbox)
        requests.post(inbox, json=r, headers=sign_headers(u, API_CONTENT_HEADERS))
      return 202
    abort(400)

class user(Resource):
  def get(self, handle):
    print('get user')
    if check_accept_headers(request):
      u = find_user_or_404(handle)

      if request.args.get('get') == 'main-key':
        return u['publicKey']['publicKeyPem'].decode('utf-8')

      user =  {
               '@context': u['@context'],
               'id': u['@id'],
               'followers': u['followers'],
               'following': u['following'],
               'icon': {'type': 'Image', 'url': u['avatar']},
               'inbox': u['inbox'],
               'manuallyApprovesFollowers': u['manuallyApprovesFollowers'],
               'name': u['name'],
               'outbox': u['outbox'],
               'preferredUsername': u['username'],
               'publicKey': {'id': u['@id']+'#main-key', 'owner': u['@id'], 'publicKeyPem': u['publicKey']['publicKeyPem'].decode('utf-8')},
               'summary': '',
               'type': u['type'],
               'url': u['url']
              }

      return user, sign_headers(u, API_CONTENT_HEADERS)
    abort(406)

class get_post(Resource):
  def get(self, handle, post_id):
    post = find_post_or_404(handle, post_id)
    if check_accept_headers(request):
      return post['object']
    return 'template yet to be written'

class get_post_activity(Resource):
  def get(self, handle, post_id):  
    post = find_post_or_404(handle, post_id)
    if check_accept_headers(request):
      return post
    return 'template yet to be written'    

# url handling
rest_api.add_resource(following, '/<string:handle>/following', subdomain='api')
rest_api.add_resource(followers, '/<string:handle>/followers', subdomain='api')
rest_api.add_resource(liked, '/<string:handle>/liked', subdomain='api')
rest_api.add_resource(inbox, '/<string:handle>/inbox', subdomain='api')
rest_api.add_resource(feed, '/<string:handle>/feed', subdomain='api')
rest_api.add_resource(user, '/user/<string:handle>')
rest_api.add_resource(get_post, '/<string:handle>/<string:post_id>', subdomain='api')
rest_api.add_resource(get_post_activity, '/<string:handle>/<string:post_id>/activity', subdomain='api')