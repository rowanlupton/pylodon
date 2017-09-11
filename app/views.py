from app import app, lm
from flask import Flask, render_template, request, session, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from bson.objectid import ObjectId
from flask_pymongo import PyMongo
from activipy import vocab

from .forms import userLogin, userRegister, composePost
from .users import User
# from .emails import lostPassword, checkToken

mongo = PyMongo(app)

@lm.user_loader
def load_user(handle):
    u = mongo.db.users.find_one({"id": handle})
    if not u:
        return None
    return User(u['id'])

def getAllPosts():
	return mongo.db.posts.find()

@app.route('/')
@login_required
def index():
	posts = getAllPosts()
	return render_template('index.html', posts=posts, mongo=mongo)


@app.route('/login', methods=['GET', 'POST'])
def login():
	form = userLogin()
	if form.validate_on_submit():
		user = mongo.db.users.find_one({'id': form.handle.data + '@populator.smilodon.social'})
		if user and User.validate_login(user['password'], form.password.data):
			user_obj = User(user['id'])
			login_user(user_obj)
			flash("Logged in successfully!", category='success')
			return redirect(request.args.get("next") or url_for('index'))
		else:
			flash('wrong username or password', category='error')
	return render_template('login.html', form=form)

def returnNewUser(handle, displayName, email, passwordHash):
	return 	{	
						'id': handle+'@populator.smilodon.social', 
						'context': 'https://www.w3.org/ns/activitystreams', 
						'preferredUsername': displayName, 
						'name': displayName, 
						'email': email, 
						'password': passwordHash, 
						'type': 'Person', 
						'following': 'http://populator.smilodon.social/'+handle+'following.json', 
						'followers': 'http://populator.smilodon.social/'+handle+'followers.json', 
						'liked': 'http://populator.smilodon.social/'+handle+'liked.json', 
						'inbox': 'http://populator.smilodon.social/'+handle+'inbox.json', 
						'outbox': 'http://populator.smilodon.social/'+handle+'feed.json', 
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
				return render_template('registration.html', form=form)
		else:
			flash("passwords did not match")
			return render_template('registration.html', form=form)
	return render_template('registration.html', form=form)


@app.route('/compose', methods=['GET', 'POST'])
@login_required
def compose():
	form = composePost()
	if form.validate_on_submit():
		putData = {'text': form.text.data, 'poster': current_user.handle}
		mongo.db.posts.insert_one(putData)
		return redirect(url_for('index'))
	return render_template('compose.html', form=form)