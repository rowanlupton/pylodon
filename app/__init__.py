from flask import Flask, logging
from flask_login import LoginManager
from flask_mail import Mail
from flask_pymongo import PyMongo
from flask_restful import Api
from flask_sslify import SSLify


app = Flask(__name__)
app.config.from_object('config')
lm = LoginManager()

lm.init_app(app)
lm.login_view = 'login'

mail = Mail(app)
mongo = PyMongo(app)
rest_api = Api(app)
sslify = SSLify(app, subdomains=True, permanent=True)


from app import views