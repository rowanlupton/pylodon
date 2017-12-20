from flask import Flask
from flask_pymongo import PyMongo
from flask_sslify import SSLify

app = Flask(__name__)
app.config.from_object('config')

mongo = PyMongo(app)
sslify = SSLify(app, subdomains=True, permanent=True)
