from app import app, lm, api, mongo
from config import API_HEADERS
from .forms import userLogin, userRegister, composePost
from .users import User
from .utilities import find_user_or_404, get_logged_in_user, createPost
# from .emails import lostPassword, checkToken

from flask import Flask, render_template, request, session, flash, redirect, url_for, jsonify, abort
from flask_login import login_user, logout_user, login_required, current_user
import requests, json

app.register_blueprint(api.api)


###################### SET-UP ######################
@lm.user_loader
def load_user(handle):
    u = mongo.db.users.find_one({"id": handle})
    if not u:
        return None
    return User(u['id'])

SERVER_URL = 'http://populator.smilodon.social/'


#################### REAL STUFF ####################

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
  posts = mongo.db.posts.find()

  return render_template('index.html', posts=posts, mongo=mongo)

@app.route('/notifications')
@login_required
def notifications():
  u = get_logged_in_user()
  r = requests.get(u['inbox'], headers=API_HEADERS)

  return render_template('index.html', posts=r.json()['items'], mongo=mongo)

@app.route('/compose', methods=['GET', 'POST'])
@login_required
def compose():
  u = get_logged_in_user()
  form = composePost()
  if form.validate_on_submit():
    u = get_logged_in_user()

    to = [u['outbox']]
    if form.to.data:
      to.append(form.to.data)

    post = createPost(form.text.data, u['name'], u['id'], to)

    requests.post(u['outbox'], data=post, headers=API_HEADERS)
    return redirect(request.args.get("next") or url_for('index'))
  return render_template('compose.html', form=form, mongo=mongo)


################### LOG IN/OUT ###################
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
  return   {  
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


#################### USER ROUTES ####################

@app.route('/<handle>')
def viewFeed(handle):
  u = find_user_or_404(handle)
  r = requests.get(u['outbox'], headers=API_HEADERS)
  return render_template('feed.html', posts=r.json()['items'], mongo=mongo)
