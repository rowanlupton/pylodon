from app import app, mongo
from config import API_CONTENT_HEADERS
from .utilities import sign_headers

from dicttoxml import dicttoxml
from flask import Blueprint, jsonify, render_template, request, Response
from urllib.request import unquote

webfinger = Blueprint('webfinger', __name__, template_folder='templates')

@webfinger.route('/host-meta')
def host_meta():
  print('in host_meta')
  return render_template('host-meta.xml', url_root=request.url_root)

@webfinger.route('/webfinger')
def get_user_info(**kwargs):
  print('in get_user_info')
  user_id = unquote(request.args['resource'])
  if 'rel' in request.args:
    rel = request.args['rel']
  acct = user_id[5:]
  u = mongo.db.users.find_one({'acct': acct})

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
            }
          ]
        }
  resp_xml = render_template('webfinger_user.xml', resp=resp)

  if request.headers.get('accept'):
    if 'application/xrd+xml' in request.headers['accept']:
      return Response(resp_xml, mimetype='application/xrd+xml', content_type='application/xrd+xml')

  return jsonify(resp), sign_headers(u, API_CONTENT_HEADERS)

def webfinger_find_user():
  pass
