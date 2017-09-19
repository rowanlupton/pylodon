from app import app, mongo

from flask import Blueprint, request, jsonify
from urllib.request import unquote

webfinger = Blueprint('webfinger', __name__, template_folder='templates')

@webfinger.route('/')
def get_user_info(**kwargs):
	acct = request.args['resource']
	u = mongo.db.users.find_one({'id': acct})

	jrd = {
					'subject': u['acct'],
					'aliases': [],
					'properties': {
						'http://schema.org/name': u['name']
					},
					'links': [
					{
						'rel': 'http://webfinger.net/rel/profile-page',
						'href': 'https://populator.smilodon.social/roo'
					}
					]
				}

	return jsonify(jrd)


