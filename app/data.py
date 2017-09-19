from app import mongo
from .models import User, Client, Token

import bcrypt, json
from bson import json_util
from datetime import datetime, timedelta
from werkzeug.security import gen_salt, generate_password_hash

class Storage(object):

	@staticmethod
	def get_user(username, password):
		u = mongo.db.users.find_one({'username': username})
		if u and password:
			if User.validate_login(u['password'], password):
				return User(u['username'])

	@staticmethod
	def get_client(client_id):
		c = mongo.db.clients.find_one({'id': client_id})
		return Client(c)

	@staticmethod
	def get_token(access_token=None, refresh_token=None):
		if not (access_token or refresh_token):
			return None

		if access_token:
			field, value = 'access_token', access_token
		elif refresh_token:
			field, value = 'refresh_token', refresh_token

		t = mongo.db.tokens.find_one({field: value})
		t = Token(t)
		if t is None:
			return None

		u = mongo.db.users.find_one({id.collection: t.user_id})
		t.user = User(u['username'])

		return t

	@staticmethod
	def save_token(token, request, *args, **kwargs):
		client_id = request.client.client_id
		username = request.user.username

		mongo.db.tokens.remove({'client_id': client_id, 'user_id': user_id})

		expires_in = token.get('expires_in')
		expires = datetime.utcnow() + timedelta(seconds=expires_in)

		token = Token(
			client_id=request.client.client_id,
			user_id=username,
			token_type=token['token_type'],
			access_token=token['access_token'],
			refresh_token=token['refresh_token'],
			expires=expires
			)

		spec = {'username': username, 'client_id': client_id}

		mongo.db.tokens.update(sepc, token.json(), upsert=True)

	@staticmethod
	def generate_client():
		client = Client()
		client.client_id = gen_salt(40)
		client.client_type = 'public'
		mongo.db.clients.insert(client.json())
		return client

	@staticmethod
	def save_user(username, password):
		p = User.hash_password(password)
		user = User(username=username, hashpw=p)
		user.id = mongo.db.users.insert(user.json())
		return user

	@staticmethod
	def all_users():
		users = mongo.db.users.find()
		users_sanitized = json.loads(json_util.dumps(users.json()))
		return users_sanitized

	@staticmethod
	def all_clients():
		clients = mongo.db.users.find()
		clients_sanitized = json.loads(json_util.dumps(clients.json()))
		return clients_sanitized

