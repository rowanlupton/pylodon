import pprint

from app import app, mongo
from config import API_CONTENT_HEADERS
from .utilities import sign_headers

from dicttoxml import dicttoxml
from flask import Blueprint, jsonify, render_template, request, Response
from urllib.request import unquote

webfinger = Blueprint('webfinger', __name__, template_folder='templates')

@webfinger.route('/host-meta')
def host_meta():
  return render_template('host-meta.xml', url_root=request.url_root)

@webfinger.route('/webfinger')
def get_user_info(**kwargs):
  user_id = unquote(request.args['resource'])
  if 'rel' in request.args:
    rel = request.args['rel']
  acct = user_id[5:]
  u = mongo.db.users.find_one({'acct': acct})

  resp = {
          'subject': 'acct:'+u['acct'],
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
              'href': u['id'],
              'rel': 'self',
              'type': 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'
            }
          ]
        }
  


  if request.headers.get('Accept'):
    if 'application/xrd+xml' in request.headers['Accept']:
      resp_xml = render_template('webfinger_user.xml', resp=resp)
      return Response(resp_xml, mimetype='application/xrd+xml', headers=(sign_headers(u, {'Content-Type': 'application/xrd+xml'})))

  resp = jsonify(resp)
  resp.headers = sign_headers(u, {'Content-Type': 'application/jrd+json'})

  return resp

def webfinger_find_user():
  pass
