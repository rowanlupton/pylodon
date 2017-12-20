import os

API_NAME = os.environ['api_name']
API_URI = os.environ['api_uri']
SERVER_NAME = os.environ['server_name']
SERVER_URI = os.environ['server_uri']

WTF_CSRF_ENABLED = True
SECRET_KEY = os.environ['secret_key']
DB_NAME = 'Cluster0'

MONGO_URI = 'mongodb://rowanlupton:'+os.environ['mongodb-password']+'@cluster0-shard-00-00-jjly0.mongodb.net:27017,cluster0-shard-00-01-jjly0.mongodb.net:27017,cluster0-shard-00-02-jjly0.mongodb.net:27017/smilodon?ssl=true&replicaSet=Cluster0-shard-0&authSource=admin'
MONGO_DBNAME = 'Cluster0'

valid_header = 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"'
CONTENT_HEADERS = {'Content-Type': valid_header}
ACCEPT_HEADERS = {'Accept': valid_header}
# specified by ActivityPub/ActivityStreams
VALID_HEADERS = (
    'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
    'application/ld+json; profile=\'https://www.w3.org/ns/activitystreams\'',
    'application/activity+json')
STRICT_HEADERS = True
