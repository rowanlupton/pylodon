# pylodon

[![Join the chat at https://gitter.im/pylodon/Lobby](https://badges.gitter.im/pylodon/Lobby.svg)](https://gitter.im/pylodon/Lobby?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

![pylodon](docs/pylodon.png)
*image courtesy of [@banjofox](https://dev.glitch.social/@banjofox)*

## Setup

Create a virtualenv (e.g. `virtualenv -p python3 venv`), activate it (e.g. `. venv/bin/activate`), and then `pip install -r requirements.txt`. *(Make sure it's a Python3 environment; some of our dependencies require it.)*

Create an account with [MongoDB's cloud service](https://www.mongodb.com/cloud/atlas); it's free for a very small cluster. Set up an admin user with a separate password, create an IP whitelist and connect to the database cluster to make sure it's working. I use a blanket whitelist, and Atlas complains at me every time. (Install `mongodb` to your machine, with Homebrew, for example.)

Docs:
* [MongoDB Atlas docs: Getting Started](https://docs.atlas.mongodb.com/getting-started/)

## Config

Update `config.py` wherever the information looks inadequate (e.g. anything that says .rowan.website should have your own domain).

Create a `.env` file (or otherwise configure environment variables), based off of the included `.env.example`. This is conveniently loaded in by python-dotenv.

For local development, you probably want to leave SSLify disabled (`STRICT_HTTPS` in `config.py`), to access the server over HTTP rather than HTTPS. The `STRICT_HEADERS` config variable is also disabled by default, so that you don't have to worry about content headers to debug the API server.

## Run it!

```
$ . venv/bin/activate
$ gunicorn run:app
```