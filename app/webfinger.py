from app import app, mongo

from flask import Blueprint, request
from urllib.request import unquote

webfinger = Blueprint('webfinger', __name__, template_folder='templates')

@webfinger.route('/')
def get_user_info(**kwargs):
	acct = request.args['resource']
	u = mongo.db.users.find_one({'id': acct})

	returnMe = {
							'subject': u['acct'],
							'aliases': [
								'http://populator.smilodon.social/roo'
							],
							'properties': {
								'http://schema.org/name': u['name']
							},
							'links': [
							{
								'rel': 'http://webfinger.net/rel/profile-page',
								'href': 'http://populator.smilodon.social/roo'
							}
							]
						}

	return str(returnMe)


