import os

API_NAME = os.environ['api_name']
API_URI = os.environ['api_uri']

WTF_CSRF_ENABLED = True
SECRET_KEY = os.environ['secret_key']
DB_NAME = 'Cluster0'

MONGO_URI = os.environ['mongodb_uri']
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
STRICT_HTTPS = False
