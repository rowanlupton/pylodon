from app import mongo
from config import API_ACCEPT_HEADERS, VALID_HEADERS, DEFAULT_CONTEXT
from .crypto import generate_keys
from .api.utilities import find_user_or_404, get_time, sign_object

from activipy import vocab
from flask import abort, request, url_for
from flask_login import current_user
from httpsig import HeaderSigner, Signer
from httpsig.requests_auth import HTTPSignatureAuth
from webfinger import finger
from werkzeug.http import http_date, parse_date
import datetime, json, requests


def find_post_or_404(handle, post_id):
  id = request.url_root+'api/'+handle+'/'+post_id+'/activity'
  p = mongo.db.posts.find_one({'id': id}, {'_id': False})
  if not p:
    abort(404)
  return p
def get_logged_in_user():
  u = mongo.db.users.find_one({'id': current_user.get_id()})
  if not u:
    abort(404)
  return u

def createPost(content, handle, to, cc):
  u = find_user_or_404(handle)
  
  post_number = str(u['metrics']['post_count'])
  id = request.url_root+'api/'+u['username']+'/posts/'+post_number
  note_url = request.url_root+'@'+u['username']+'/'+post_number
  
  time = get_time()

  create =  {
            'id': id+'/activity',
            'type': 'Create',
            '@context': DEFAULT_CONTEXT,
            'actor': u['id'],
            'published': time,
            'to': to,
            'cc': cc,
            'object': {
                        'id': id,
                        'type': 'Note',
                        'summary': None,
                        'content': content,
                        'inReplyTo': None,
                        'published': time,
                        'url': note_url,
                        'attributedTo': u['id'],
                        'to': to,
                        'cc': cc,
                        'sensitive': False
                      },
            'signature': {
              'created': time,
              'creator': u['id']+'?get=main-key',
              'signatureValue': sign_object(u, content),
              'type': 'rsa-sha256'
            }
          }
  return json.dumps(create)
def createLike(actorAcct, post):
  to = post['attributedTo']
  if posts.get('to'):
    for t in post['to']:
      to.append(t)
      
  return vocab.Like(
                    context=DEFAULT_CONTEXT,
                    actor=actorAcct,
                    to=to,
                    object=post['id'])
def createFollow(actorAcct, otherUser):
  return vocab.Follow(
                      id=None,
                      context=DEFAULT_CONTEXT,
                      actor=actorAcct,
                      object=vocab.User(otherUser['id']))
def createAccept(followObj, to):
  acceptObj = {
                "@context": DEFAULT_CONTEXT,
                'type': 'Accept',
                'to': to,
                'object': followObj
              }
  return acceptObj
def createReject(followObj, to):
  rejectObj = {
                'type': 'Reject',
                'to': to,
                'object': followObj
              }
  return rejectObj