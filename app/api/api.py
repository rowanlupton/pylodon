from app import mongo
from config import STRICT_HEADERS
from .utilities import accept_headers, as_asobj, check_headers, content_headers, find_post, find_user

from activipy import core, vocab
from flask import abort, Blueprint, request, Response
from flask_restful import Resource

import json
import requests

api = Blueprint('api', __name__, template_folder='templates')


@api.before_request
def check_headers_before_request():
    """
    will abort with an appropriate HTTP error code if headers are wrong
    """
    if STRICT_HEADERS:
        check_headers(request=request)


@api.before_request
def add_at_prefix():
    r = request.get_json()
    keys = ['id', 'type']
    for key in keys:
        if r.get(key, False):
            r['@'+key] = r.pop(key)


@api.route('/<handle>/followers')
def following(handle):
    """
    returns a Collection of all Actors' @ids who follow given Actor
    """
    u = find_user(handle)

    following = u.get('following_coll', [])
    return Response(json.dumps(following), headers=content_headers(u))


@api.route('/<handle>/followers')
def followers(handle):
    """
    returns a Collection of all Actors' @ids who follow given Actor
    """
    print('followers get')
    u = find_user(handle)

    followers = u.get('followers_coll', [])
    return Response(json.dumps(followers), headers=content_headers(u))


@api.route('/<handle>/liked')
def liked(handle):
    """
    returns a Collection of Objects that given Actor has Liked
    """
    u = find_user(handle)
    likes = []

    for post in mongo.db.posts.find({'object.liked_coll': u['@id']}):
        likes.append(post['object'])

    return Response(json.dumps(likes), headers=content_headers(u))


@api.route('/<handle>/inbox', methods=['GET', 'POST'])
def inbox(handle):
    if request.method == 'GET':
        """
        think of this as the "Home" feed on mastodon. returns all Objects
        addressed to the user. this should require authentication
        """
        u = find_user(handle)
        items = list(mongo.db.posts.find({'to': u['@id']}, {'_id': False}).sort('published', -1))

        resp = vocab.OrderedCollection(
            u['inbox'],
            totalItems=len(items),
            orderedItems=items)

        return Response(resp, headers=content_headers(find_user(handle)))

    if request.method == 'POST':
        """
        deduplicates requests, and adds them to the database. in some cases
        (e.g. Follow requests) it automatically responds, pending fuller API
        and UI implementation
        """
        print('inbox post')
        u = find_user(handle)
        r = request.get_json()

        if r['@type'] == 'Like':
            print('received Like')
            mongo.db.posts.update_one({'id': r['object']}, {'$push': {'object.liked_coll': r['actor']}}, upsert=True)

        elif r['@type'] == 'Follow':
            if u.get('followers_coll'):
                if u['followers_coll'].get('actor'):
                    return 400

            mongo.db.users.update_one({'id': u['@id']}, {'$push': {'followers_coll': r['actor']}}, upsert=True)
            to = requests.get(r['actor'], headers=accept_headers(u)).json()['inbox']
            accept = vocab.accept(
                            to=to,
                            object=r.get_json()).json()
            headers = content_headers(u)

            requests.post(to, json=accept, headers=headers)
            return 202

        elif r['@type'] == 'Accept':
            print('received Accept')
            mongo.db.users.update_one({'id': u['@id']}, {'$push': {'following_coll': r['object']['actor']}}, upsert=True)
            return 202

        elif r['@type'] == 'Create':
            # this needs more stuff, like creating a user if necessary
            if not mongo.db.posts.find({'id': r['@id']}):
                mongo.db.posts.insert_one(r['object'].json())
                return 202

        else:
            print('other type')
            print(r)
        abort(400)


@api.route('/<handle>/feed', methods=['GET', 'POST'])
def feed(handle):
    if request.method == 'GET':
        """
        per AP spec, returns a reverse-chronological OrderedCollection of
        items in the outbox, pending privacy settings
        """
        print('feed get')
        u = find_user(handle)

        items = list(mongo.db.posts.find({'object.attributedTo': u['@id']}, {'_id': False}).sort('published', -1))

        resp = vocab.OrderedCollection(
            u['outbox'],
            totalItems=len(items),
            orderedItems=items)

        return Response(json.dumps(resp.json()), headers=content_headers(u))

    if request.method == 'POST':
        """
        adds objects that it receives to mongodb and sends them along
        to appropriate Actor inboxes
        """
        r = core.ASObj(request.get_json(), vocab.BasicEnv)
        u = find_user(handle)

        # if it's a note it turns it into a Create object
        if 'Note' in r.types:

            obj = r.get_json()
            r = vocab.Create(
                obj['@id']+'/activity',
                actor=u['@id'],
                published=obj['published'],
                to=obj['to'],
                bto=obj['bto'],
                cc=obj['cc'],
                bcc=obj['bcc'],
                audience=obj['audience'],
                obj=obj)

        if 'Create' in r.types:
            if r['object']['@type'] != 'Note':
                print(str(r))
                print('not a note')
                abort(403)

            mongo.db.users.update({'acct': u['acct']}, {'$inc': {'metrics.post_count': 1}})

        elif 'Like' in r.types:
            if u['acct'] not in mongo.db.posts.find({'@id': r['object']['@id']})['likes']:
                mongo.db.posts.update({'@id': r['object']['@id']}, {'$push': {'likes': u['acct']}})

        elif 'Follow' in r.types:
            pass

        elif 'Update' in r.types:
            """
            update user object on other servers
            """
            pass

        elif 'Delete' in r.types:
            """
            notify other servers that an object has been deleted
            """
            pass

        elif 'Add' in r.types:
            """
            """
            pass

        elif 'Remove' in r.types:
            """
            """
            pass

        elif 'Announce' in r.types:
            """
            """
            pass

        elif 'Block' in r.types:
            """
            """
            pass

        elif 'Undo' in r.types:
            """
            """
            pass

        recipients = []
        r = r.json()

        for group in ['to', 'bto', 'cc', 'bcc', 'audience']:
            addresses = r.get(group, [])
            recipients.extend(addresses)

        for address in addresses:
            requests.post(address, json=r, headers=content_headers(u))
        mongo.db.posts.insert_one(r)

        return 202


@api.route('/<handle>')
def user(handle):
    """
    returns either the user's public key or a Person object with
    sensitive info removed
    """
    u = find_user(handle)

    if request.args.get('get') == 'main-key':
        return u['publicKey']['publicKeyPem'].decode('utf-8')

    headers = content_headers(u)

    # important not to send these things around
    entries = ('email', 'privateKey', 'password')
    for entry in entries:
        u.pop(entry)
    u['publicKey']['publicKeyPem'] = u['publicKey']['publicKeyPem'].decode('utf-8')

    return Response(json.dumps(u), headers=headers)


@api.route('/<handle>/<post_id>')
def get_post(handle, post_id):
    """
    """
    post = find_post(handle, post_id)['object']
    headers = content_headers(find_user(handle))
    return Response(post, headers=headers)


@api.route('/<handle>/<post_id>/activity')
def get_post_activity(handle, post_id):
    """
    """
    post = find_post(handle, post_id)
    headers = content_headers(find_user(handle))
    return Response(post, headers=headers)
