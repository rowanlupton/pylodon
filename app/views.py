from app import app, lm
from flask import Flask, render_template, request, session, flash, redirect, url_for, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_restful import Resource, Api, marshal_with
from bson import ObjectId, json_util
import json
from flask_pymongo import PyMongo
from activipy import vocab

from .forms import userLogin, userRegister, composePost
from .users import User
# from .emails import lostPassword, checkToken

mongo = PyMongo(app)
api = Api(app)

@lm.user_loader
def load_user(handle):
    u = mongo.db.users.find_one({"id": handle})
    if not u:
        return None
    return User(u['id'])

@app.route('/')
@login_required
def index():
	posts = mongo.db.posts.find()
	return render_template('index.html', posts=posts, mongo=mongo)

@app.route('/login', methods=['GET', 'POST'])
def login():
	form = userLogin()
	if form.validate_on_submit():
		user = mongo.db.users.find_one({'id': request.base_url + form.handle.data})
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
	return mongo.db.following.find({'id': handle+'@populator.smilodon.social'})

@app.route('/<handle>/followers')
def followers(handle):
	return mongo.db.followers.find({'id': handle+'@populator.smilodon.social'})

@app.route('/<handle>/liked')
def liked(handle):
	return mongo.db.liked.find({'id': handle+'@populator.smilodon.social'})

@app.route('/<handle>/inbox', methods=["POST"])
def inbox(handle):
	return 'foo'

@app.route('/<handle>/feed', methods=["GET", "POST"])
def feed(handle):
	if request.method == 'POST':
		user = mongo.db.users.find_one({'id': request.url_root + handle})
		print(request.url_root + handle)
		post = createPost(request.form['text'], user['name'], user['id'], user['outbox'])
		mongo.db.posts.insert_one(post.json())
		return redirect(request.args.get("next") or url_for('index'))
	else:
		feedObj = vocab.OrderedCollection(items=mongo.db.posts.find({'actor.@id': 'http://populator.smilodon.social/'+handle}).sort('_id', -1))
		if request.headers.get('application/ld+json; profile="https://www.w3.org/ns/activitystreams"') or request.headers.get('application/activity+json'):
			return feedObj
		else:
			return render_template('feed.html', posts=feedObj, mongo=mongo)
