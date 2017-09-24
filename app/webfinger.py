from app import app, mongo

from flask import Blueprint, jsonify, request
from urllib.request import unquote
from .utilities import sign_headers

webfinger = Blueprint('webfinger', __name__, template_folder='templates')

@webfinger.route('/host-meta')
def host_meta():
  return render_template('host-meta.xml', url_root=request.url_root)

@webfinger.route('/webfinger')
def get_user_info(**kwargs):
  id = unquote(request.args['resource'])
  if 'rel' in request.args:
    rel = request.args['rel']
  u = mongo.db.users.find_one({'id': id})

  resp = {
          'subject': u['id'],
          'aliases': [
            request.url_root+'@'+u['username'],
            request.url_root+'api/'+u['username']
          ],
          'properties': {
            'http://schema.org/name': u['name']
          },
          'links': [
            {
              'rel': 'http://webfinger.net/rel/profile-page',
              'href': request.url_root+'@'+u['username']
            },
            {
              'href': request.url_root+'api/'+u['username'],
              'rel': 'self',
              'type': 'application/activity+json'
            },
          ]
        }

  return jsonify(resp), sign_headrs(u)


def webfinger_find_user(acct):
  pass