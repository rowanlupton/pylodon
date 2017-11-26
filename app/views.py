from app import app, lm, mongo, webfinger
from config import API_CONTENT_HEADERS, API_ACCEPT_HEADERS, API_NAME, SERVER_NAME
from .api import api
from .api.users import User
from .forms import userLogin, userRegister, composePost
from .utilities import find_user_or_404, get_logged_in_user, createPost, createLike
from .webfinger import webfinger_find_user
# from .emails import lostPassword, checkToken

from flask import Flask, render_template, request, session, flash, redirect, url_for, jsonify, abort
from flask_login import login_user, logout_user, login_required, current_user
import requests, json
from urllib.parse import unquote
# from webfinger import finger

app.register_blueprint(api.api, subdomain='api')
app.register_blueprint(webfinger.webfinger, url_prefix='/.well-known')

###################### SET-UP ######################
@lm.user_loader
def load_user(handle):
    u = mongo.db.users.find_one({"username": handle})
    if not u:
        return None
    return User(u['id'])


#################### MISCELLANEA ####################

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
  posts = mongo.db.posts.find()

  return render_template('index.html', posts=posts, mongo=mongo)

@app.route('/notifications')
@login_required
def notifications():
  u = get_logged_in_user()
  r = requests.get(u['inbox'], headers=API_CONTENT_HEADERS)

  return render_template('index.html', posts=r.json()['items'], mongo=mongo)

@app.route('/compose', methods=['GET', 'POST'])
@login_required
def compose():
  form = composePost()
  if form.validate_on_submit():
    u = get_logged_in_user()

    to = ['https://www.w3.org/ns/activitystreams#Public']
    if u.get('followers_coll'):
      for t in u['followers_coll']:
        to.append(t)
    cc = []
    if form.to.data:
      field = form.to.data.split(',')
      for f in field:
        cc.append(f)

    create = createPost(form.text.data, u['username'], to, cc)

    requests.post(u['outbox'], data=create, headers=API_CONTENT_HEADERS)
    return redirect(request.args.get("next") or url_for('index'))
  return render_template('compose.html', form=form, mongo=mongo)


#################### PROFILE ####################
@app.route('/<handle>')
def redirectToViewFeed(handle):

  return redirect(unquote(url_for('viewFeed', handle=handle)))

@app.route('/@<handle>')
def viewFeed(handle):
  u = find_user_or_404(handle)
  r = requests.get(u['outbox'], headers=API_ACCEPT_HEADERS).json()
  return render_template('feed.html', posts=r['orderedItems'], mongo=mongo)

@app.route('/@<handle>/<postID>')
def viewPost(handle, postID):
  p = mongo.db.posts.find_one({'id': 'https://'+API_NAME+'/'+handle+'/posts/'+postID})
  return str(p)
  return render_template('feed.html', posts=p, mongo=mongo)

@app.route('/@<handle>/<postID>/like')
@login_required
def likePost(handle, postID):
  loggedin_u = get_logged_in_user()
  u = find_user_or_404(handle)
  p = mongo.db.posts.find_one({'@id': request.url_root+handle+'/posts/'+postID})
  like = createLike(u['acct'], p)
  requests.post(loggedin_u['outbox'], data=json.dumps(like.json()), headers=API_CONTENT_HEADERS)
  return redirect(request.args.get("next") or url_for('index'))

################### LOG IN/OUT ###################
@app.route('/login', methods=['GET', 'POST'])
def login():
  form = userLogin()
  if form.validate_on_submit():
    password = form.password.data
    user = find_user_or_404(form.handle.data)
    if user and User.validate_login(user['password'], form.password.data):
      user_obj = User(user['username'])
      login_user(user_obj)
      flash("Logged in successfully!", category='success')
      return redirect(request.args.get("next") or url_for('index'))
    else:
      flash('wrong username or password', category='error')
  return render_template('login.html', form=form, mongo=mongo)

@app.route('/register', methods=['GET', 'POST'])
def register():
  form = userRegister()
  if form.validate_on_submit():
    if form.password.data == form.passwordConfirm.data:
      j = dict( handle=form.handle.data, 
                email=form.email.data, 
                displayName=form.displayName.data, 
                password=form.password.data)
      http_code = requests.post(url_for('new_user'), json=j, headers=API_CONTENT_HEADERS).json()
      if http_code is 200:
        return redirect(request.args.get("next") or url_for('index'))
      elif http_code is 409:
        flash("username taken")
        return render_template('registration.html', form=form, mongo=mongo)
        
    else:
      flash("passwords did not match")
      return render_template('registration.html', form=form, mongo=mongo)
  return render_template('registration.html', form=form, mongo=mongo)

@app.route('/logout')
def logout():
  logout_user()
  return redirect(url_for('index'))

