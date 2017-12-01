from flask import request, url_for, make_response, current_app, \
                  _app_ctx_stack as stack
from werkzeug.routing import BuildError
from jinja2 import Markup

import functools

__all__ = ('init_publisher', 'publisher',)

HEADER_VALUE = '<%s>; rel="self", <%s>; rel="hub"'
SELF_LINK = '<link rel="self" href="%s" />'
HUB_LINK = '<link rel="hub" href="%s" />'


def init_publisher(app):
    """Calling this with your flask app as argument is required for the
    publisher decorator to work.

    """
    @app.context_processor
    def inject_links():
        return {
            'websub_self_url': stack.top.websub_self_url,
            'websub_hub_url': stack.top.websub_hub_url,
            'websub_self_link': stack.top.websub_self_link,
            'websub_hub_link': stack.top.websub_hub_link,
        }


def publisher(self_url=None, hub_url=None):
    """This decorator makes it easier to implement a websub publisher. You use
    it on an endpoint, and Link headers will automatically be added. To also
    include these links in your template html/atom/rss (and you should!) you
    can use the following to get the raw links:

    - {{ websub_self_url }}
    - {{ websub_hub_url }}

    And the following to get them wrapped in <link tags>:

    - {{ websub_self_link }}
    - {{ websub_hub_link }}

    If hub_url is not given, the hub needs to be a flask_websub one and the
    hub and publisher need to share their application for the url to be
    auto-discovered. If that is not the case, you need to set
    config['HUB_URL'].

    If self_url is not given, the url of the current request will be used. Note
    that this includes url query arguments. If this is not what you want,
    override it.

    """
    def decorator(topic_view):
        @functools.wraps(topic_view)
        def wrapper(*args, **kwargs):
            nonlocal hub_url, self_url

            if not self_url:
                self_url = request.url
            if not hub_url:
                try:
                    hub_url = url_for('websub_hub.endpoint', _external=True)
                except BuildError:
                    hub_url = current_app.config['HUB_URL']

            stack.top.websub_self_url = self_url
            stack.top.websub_hub_url = hub_url
            stack.top.websub_self_link = Markup(SELF_LINK % self_url)
            stack.top.websub_hub_link = Markup(HUB_LINK % hub_url)

            resp = make_response(topic_view(*args, **kwargs))
            resp.headers.add('Link', HEADER_VALUE % (self_url, hub_url))
            return resp
        return wrapper
    return decorator
