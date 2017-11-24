from flask import Flask, logging
from flask_login import LoginManager
from flask_mail import Mail
from flask_pymongo import PyMongo
from flask_restful import Api


api = Flask(__name__)
api.config.from_object('config')

mongo = PyMongo(app)
rest_api = Api(app)



from api import api