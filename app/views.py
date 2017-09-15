from app import app, lm
from flask import Flask, render_template, request, session, flash, redirect, url_for, jsonify, make_response
from flask_login import login_user, logout_user, login_required, current_user
from bson import ObjectId, json_util
import json, requests
from flask_pymongo import PyMongo
from activipy import vocab

from .forms import userLogin, userRegister, composePost
from .users import User
# from .emails import lostPassword, checkToken

mongo = PyMongo(app)

SERVER_URL = 'http://populator.smilodon.social/'
API_HEADERS = {'Content-Type': 'application/ld+json', 'profile': 'https://www.w3.org/ns/activitystreams'}

@lm.user_loader
def load_user(handle):
    u = mongo.db.users.find_one({"id": handle})
    if not u:
        return None
    return User(u['id'])

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
	user = mongo.db.users.find_one({'id': current_user.get_id()})

	r = requests.get(user['inbox'], headers=API_HEADERS)
	return render_template('index.html', posts=r.json()['items'], mongo=mongo)


@app.route('/login', methods=['GET', 'POST'])
def login():
	form = userLogin()
	if form.validate_on_submit():
		handle = form.handle.data
		password = form.password.data
		user = mongo.db.users.find_one({'id':  form.handle.data})
		if user and User.validate_login(user['password'], form.password.data):
			user_obj = User(user['id'])
			login_user(user_obj)
			flash("Logged in successfully!", category='success')
			return redirect(request.args.get("next") or url_for('index'))
		else:
			flash('wrong username or password', category='error')
	return render_template('login.html', form=form, mongo=mongo)

def returnNewUser(handle, displayName, email, passwordHash):
	return 	{	
						'id': handle+'@populator.smilodon.social', 
						'context': 'https://www.w3.org/ns/activitystreams', 
						'name': displayName, 
						'email': email, 
						'password': passwordHash, 
						'type': 'Person', 
						'following': 'http://populator.smilodon.social/'+handle+'/following.json', 
						'followers': 'http://populator.smilodon.social/'+handle+'/followers.json', 
						'liked': 'http://populator.smilodon.social/'+handle+'/liked.json', 
						'inbox': 'http://populator.smilodon.social/'+handle+'/inbox.json', 
						'outbox': 'http://populator.smilodon.social/'+handle+'/feed.json', 
						'summary': '', 
						'icon': ''
					}

@app.route('/register', methods=['GET', 'POST'])
def register():
	form = userRegister()
	if form.validate_on_submit():
		if form.password.data == form.passwordConfirm.data:
			if mongo.db.users.find({"id": form.handle.data}) != None:
				passwordHash = User.hash_password(form.password.data)
				putData = returnNewUser(form.handle.data, form.displayName.data, form.email.data, passwordHash)
				mongo.db.users.insert_one(putData)
				return redirect(request.args.get("next") or url_for('index'))
			else:
				flash("username taken")
				return render_template('registration.html', form=form, mongo=mongo)
		else:
			flash("passwords did not match")
			return render_template('registration.html', form=form, mongo=mongo)
	return render_template('registration.html', form=form, mongo=mongo)

def createPost(text, name, id, receivers):
	return vocab.Create(
											actor=vocab.Person(
													id,
													displayName=name),
											to=[receivers],
											object=vocab.Note(
												content=text))

@app.route('/compose', methods=['GET', 'POST'])
@login_required
def compose():
	form = composePost()
	url = mongo.db.users.find_one({'id': current_user.get_id()})['outbox']
	return render_template('compose.html', form=form, url=url, mongo=mongo)




# user routes
@app.route('/<handle>/following')
def following(handle):
	return mongo.db.following.find({'id': SERVER_URL+handle})

@app.route('/<handle>/followers')
def followers(handle):
	return mongo.db.followers.find({'id': SERVER_URL+handle})



@app.route('/<handle>')
def viewFeed(handle):
	u = mongo.db.users.find_one({'id': SERVER_URL+handle})
	r = requests.get(u['outbox'], headers=API_HEADERS)
	return render_template('feed.html', posts=r.json()['items'], mongo=mongo)



######################## API ########################

@app.route('/api/<handle>/following')
def api_following(handle):
	pass

@app.route('/api/<handle>/followers')
def api_followers(handle):
	pass

@app.route('/api/<handle>/liked')
def api_liked(handle):
	pass

@app.route('/api/<handle>/inbox', methods=["GET", "POST"])
def api_inbox(handle):
	if request.method == 'POST':
		return '403'

		user = mongo.db.users.find_one({'id': SERVER_URL + handle})
		post = createPost(request.form['text'], user['name'], user['id'], user['inbox'])
		mongo.db.posts.insert_one(post.json())
		return redirect(request.args.get("next") or url_for('index'))
	elif request.method == 'GET':
		feedObj = vocab.OrderedCollection(items=mongo.db.posts.find({'to': {'$in:' [SERVER_URL+handle]}}).sort('_id', -1))
		if request.headers.get('Content-Type'):
			if (request.headers['Content-Type'] == 'application/ld+json' and request.headers['profile'] == 'https://www.w3.org/ns/activitystreams') or (request.headers['Content-Type'] == 'application/activity+json'):
				feedObj_sanitized = json.loads(json_util.dumps(feedObj.json()))
				return jsonify(feedObj_sanitized)
			else:
				pass
		else:
			pass

@app.route('/api/<handle>/feed', methods=["GET", "POST"])
def api_feed(handle):
	if request.method == 'POST':
		return '403'

		user = mongo.db.users.find_one({'id': SERVER_URL + handle})
		post = createPost(request.form['text'], user['name'], user['id'], user['outbox'])
		mongo.db.posts.insert_one(post.json())
		return redirect(request.args.get("next") or url_for('index'))

	elif request.method == 'GET':
		feedObj = vocab.OrderedCollection(items=mongo.db.posts.find({'actor.@id': SERVER_URL+handle}).sort('_id', -1))
		if request.headers.get('Content-Type'):
			if (request.headers['Content-Type'] == 'application/ld+json' and request.headers['profile'] == 'https://www.w3.org/ns/activitystreams') or (request.headers['Content-Type'] == 'application/activity+json'):
				feedObj_sanitized = json.loads(json_util.dumps(feedObj.json()))
				return jsonify(feedObj_sanitized)
			else:
				pass
		else:
			pass
