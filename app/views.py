from app import app, lm, mongo, webfinger
from config import ACCEPT_HEADERS
from .api import api
from .api.utilities import content_headers, find_user
from .forms import userLogin, userRegister, composePost
from .users import User
from .utilities import get_address, get_logged_in_user, create_like, create_post, create_user
# from .emails import lostPassword, checkToken

from flask import render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required
import requests
import json
from urllib.parse import unquote


# from webfinger import finger

app.register_blueprint(api.api, subdomain='api')
app.register_blueprint(webfinger.webfinger, url_prefix='/.well-known')


# SET-UP

@lm.user_loader
def load_user(handle):
    """
    """
    u = mongo.db.users.find_one({"username": handle})
    if not u:
        return None
    return User(u['@id'])


# MISCELLANEA

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """
    """
    posts = mongo.db.posts.find({}, {'_id': False})

    p = []

    for post in posts:
        p.append(post)
        p.append('<br/><br/><br/>')

    return str(p)
    return render_template('index.html', posts=posts, mongo=mongo)


@app.route('/notifications')
@login_required
def notifications():
    """
    """
    u = get_logged_in_user()
    r = requests.get(u['inbox'], headers=content_headers(u))

    return render_template('index.html', posts=r.json()['items'], mongo=mongo)


@app.route('/compose', methods=['GET', 'POST'])
@login_required
def compose():
    """
    """
    form = composePost()
    if form.validate_on_submit():
        u = get_logged_in_user()
        data = dict(
            to=form.to.data,
            post=form.text.data)
        addresses = dict(
            to=['https://www.w3.org/ns/activitystreams#Public'],
            bto=[],
            cc=[u['followers']],
            bcc=[],
            audience=[])

        for t in data['to'].split(','):
            addresses['to'].append(get_address(t))

        create = create_post(u, data['post'], addresses)

        requests.post(u['outbox'], json=create.json(), headers=content_headers(u))
        return redirect(request.args.get("next") or url_for('index'))
    return render_template('compose.html', form=form, mongo=mongo)


# PROFILE

@app.route('/<handle>')
def redirectToViewFeed(handle):
    """
    """
    return redirect(unquote(url_for('viewFeed', handle=handle)))


@app.route('/@<handle>')
def viewFeed(handle):
    """
    """
    u = find_user(handle)
    r = requests.get(u['outbox'], headers=ACCEPT_HEADERS).json()
    return render_template('feed.html', posts=r['orderedItems'], mongo=mongo)


@app.route('/<handle>/<postID>')
def viewPost(handle, postID):
    """
    """
    p = mongo.db.posts.find_one({'@id': request.url_root+handle+'/posts/'+postID})
    return render_template('feed.html', posts=p, mongo=mongo)


# @app.route('/<handle>/<postID>/like')
# @login_required
def likePost(handle, postID):
    """
    """
    loggedin_u = get_logged_in_user()
    u = find_user(handle)
    p = mongo.db.posts.find_one({'@id': request.url_root+handle+'/posts/'+postID})
    like = create_like(u['acct'], p)
    requests.post(loggedin_u['outbox'], data=json.dumps(like.json()), headers=content_headers(u))
    # return redirect(request.args.get("next") or url_for('index'))


# LOG IN/OUT

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    """
    form = userLogin()
    if form.validate_on_submit():
        password = form.password.data
        handle = form.handle.data
        user = find_user(handle)
        if user and User.validate_login(user['password'], password):
            user_obj = User(user['username'])
            login_user(user_obj)
            flash("Logged in successfully!", category='success')
            return redirect(request.args.get("next") or url_for('index'))
        else:
            flash('wrong username or password', category='error')
    return render_template('login.html', form=form, mongo=mongo)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    """
    form = userRegister()
    if form.validate_on_submit():
        if form.password.data == form.passwordConfirm.data:
            user = dict(
                handle=form.handle.data,
                email=form.email.data,
                displayName=form.displayName.data,
                password=form.password.data)

            if {'username': user['handle']} in mongo.db.users.find():
                flash("username taken")
                return render_template('registration.html', form=form, mongo=mongo)
            else:
                mongo.db.users.insert_one(create_user(user).json())
            return redirect(request.args.get("next") or url_for('index'))
        else:
            flash("passwords did not match")
            return render_template('registration.html', form=form, mongo=mongo)
    return render_template('registration.html', form=form, mongo=mongo)


@app.route('/logout')
@login_required
def logout():
    """
    """
    logout_user()
    return redirect(url_for('index'))
