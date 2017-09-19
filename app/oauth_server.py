from app import app, mongo
from .data import Storage
from datetime import datetime, timedelta


@oauth.clientgetter
def load_client(client_id):
	return Storage.get_client(client_id)

@oauth.grantgetter
def load_grant(client_id, code):
	return mongo.db.grants.find_one({'username'})

@oauth.grantsetter
def save_grant(client_id, code, request, *args, **kwargs):
	expires = datetime.utcnow() + timedelta(seconds=100)
	grant = Grant()