# pylodon

~[pylodon](docs/pylodon.png)

# this README is currently out of date


## Setup

Create a virtualenv, activate it, and then `pip install -r requirements.txt`. (Make sure it's a Python3 environment; some of our dependencies require it.)

Create an account with [MongoDB's cloud service](https://www.mongodb.com/cloud/atlas); it's free for a very small cluster. Set up an admin user with a separate password, create an IP whitelist and connect to the database cluster to make sure it's working. (Install `mongodb` to your machine, with Homebrew, for example.)

Docs:
* [MongoDB Atlas docs: Getting Started](https://docs.atlas.mongodb.com/getting-started/)

## Config

Update `config.py` with your MongoDB credentials/URIs (be sure to get the full URI connection string from the "Connect Your Application" dialog), your email address in the `ADMINS` list and some dummy mail server credentials.

Create a `.env` file (or otherwise configure environment variables) for your MongoDB password, API key, and other sensitive variables, based on `.env.example`. `server_name` _must_ be set to the host/port at which you'll be accessing the server; for example, for local testing you might set it to `smilodon.localhost:5000` and add `127.0.0.1 smilodon.localhost` to your `hosts` file. server_uri should be the full address and protocol that it will be found at, e.g. `https://smilodon.social`.

For local development, you may wish to disable SSLify (in `app/__init__.py`), to access the server over HTTP rather than HTTPS.

## Run it locally

Install Heroku (`brew install heroku`). (You could also use Foreman or Honcho.)

`heroku local` should run the server on your local machine. You can access the server at the server name you configured above, for example, http://smilodon.localhost:5000.