from app import app, mongo

from flask import Blueprint, request, jsonify
from urllib.request import unquote

webfinger = Blueprint('webfinger', __name__, template_folder='templates')

@webfinger.route('/')
def get_user_info(**kwargs):
  acct = request.args['resource']
  u = mongo.db.users.find_one({'acct': acct})

  jrd = {
          'subject': u['id'],
          'aliases': [],
          'properties': {
            'http://schema.org/name': u['name']
          },
          'links': [
            {
              'rel': 'http://webfinger.net/rel/profile-page',
              'href': request.host+'@'+u['username']
            },
            {
              'href': request.host+'users/'+u['username'],
              'rel': 'self',
              'type': 'application/activity+json'
            }
          ]
        }

  return jsonify(jrd)


