from flask import Flask
from flask_pymongo import PyMongo
from flask_sslify import SSLify

from config import STRICT_HTTPS

app = Flask(__name__)
app.config.from_object('config')

mongo = PyMongo(app)
if STRICT_HTTPS:
    sslify = SSLify(app, subdomains=True, permanent=True)
