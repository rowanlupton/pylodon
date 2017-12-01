from flask import url_for, current_app
import requests

import contextlib

from ..utils import uuid4, request_url, secret_too_big, A_DAY
from ..errors import SubscriberError

from .discovery import discover
from .blueprint import build_blueprint
from .events import EventMixin
from .storage import WerkzeugCacheTempSubscriberStorage, \
                     SQLite3TempSubscriberStorage, SQLite3SubscriberStorage

from ..utils import warn

__all__ = ('Subscriber', 'discover', 'WerkzeugCacheTempSubscriberStorage',
           'SQLite3TempSubscriberStorage', 'SQLite3SubscriberStorage')

NO_SECRET_WITH_HTTP = ("Only specify a secret when using https. If you did "
                       "not pass one in yourself, disable AUTO_SET_SECRET.")
LEASE_SECONDS_INVALID = "lease_seconds should be a positive decimal integer"
INVALID_HUB_URL = "Invalid hub URL (subscribing failed)"
NOT_FOUND = "Could not find subscription: "
RENEW_FAILURE = "Could not renew subscription (%s, %s)"


class Subscriber(EventMixin):
    """A subscriber takes the following constructor arguments:

    - an AbstractSubscriberStorage instance for long-term data storage
    - an AbstractTempSubscriberStorage instance for short-term data storage
    - configuration values (optional); they are (with their default values):
        - REQUEST_TIMEOUT=3: Specifies how long to wait before considering a
          request to have failed.
        - MAX_BODY_SIZE=1024 * 1024: the maximum body size of a notification,
          larger requests will be rejected. The default is 1MiB.

    It exposes the following methods:

    - subscribe
    - unsubscribe
    - renew
    - renew_close_to_expiration
    - cleanup

    It also exposes a property: blueprint, which you can use as an argument to
    app.register_blueprint().

    The subscriber of course also needs to be able to notify you when a
    notification from the hub is sent. You can register one or more functions
    to handle this for you. Similarly, you can register handlers for
    subscription successes and failures (as this is an asynchronous process,
    the above methods will only tell you about errors they can detect
    up-front.) You can pass your handler functions to:

    - add_listener; a handler should expect (topic_url, callback_url, body) as
      arguments on a notification.
    - add_error_handler; a handler should expect (topic_url, callback_url,
      reason) as arguments.
    - add_success_handler; a handler should expect (topic_url, callback_url,
      mode) as arguments. Mode is a string: either 'publish' or 'unpublish'.

    """
    def __init__(self, storage, temp_storage, **config):
        super().__init__()

        self.storage = storage
        self.temp_storage = temp_storage
        self.config = config

    def build_blueprint(self, url_prefix=''):
        """Build a blueprint that contains the endpoints for callback URLs of
        the current subscriber. Only call this once per instance. Arguments:

        - url_prefix; this allows you to prefix the callback URLs in your app.

        """
        self.blueprint_name, self.blueprint = build_blueprint(self, url_prefix)
        return self.blueprint

    def subscribe(self, **subscription_request):
        """Subscribe to a certain topic. All arguments are keyword arguments.
        They are:

        - topic_url: the url of the topic to subscribe to.
        - hub_url: the url of the hub that the topic url links to.
        - secret (optional): a secret to use in the communication. If
          AUTO_SET_SECRET is enabled (and it is by default), the library
          creates a random secret for you, unless you override it.
        - lease_seconds (optional): the lease length you request from the
          hub. Note that the hub may override it. If it's not given, the hub
          gets to decide by itself.

        Note that, while possible, it is not always necessary to find the
        topic_url and hub_url yourself. If you have a WebSub-supporting URL,
        you can find them using the discover function. That makes calling this
        function as simple as:

        subscriber.subscribe(**discover('http://some_websub_supporting.url'))

        This function returns a callback_id. This value is an implementation
        detail, so you should not ascribe any meaning to it other than it being
        a unique identifier of the subscription.

        """
        return self.subscribe_impl(mode='subscribe', **subscription_request)

    def subscribe_impl(self, callback_id=None, **request):
        # 5.1 Subscriber Sends Subscription Request
        endpoint = self.blueprint_name + '.subscription_confirmation'
        if not callback_id:
            callback_id = uuid4()
        callback_url = url_for(endpoint, callback_id=callback_id,
                               _external=True)
        args = {
            'hub.callback': callback_url,
            'hub.mode': request['mode'],
            'hub.topic': request['topic_url'],
        }
        try:
            args['hub.lease_seconds'] = request['lease_seconds']
        except KeyError:
            request['lease_seconds'] = None
        else:
            if request['lease_seconds'] <= 0:
                raise SubscriberError(LEASE_SECONDS_INVALID)
        add_secret_to_args(args, request, is_secure(request['hub_url']))
        # ten minutes should be enough time for the hub to answer. If the hub
        # didn't answer for so long, we can forget about the request.
        request['timeout'] = 10 * 60
        self.temp_storage[callback_id] = request
        try:
            response = self.safe_post_request(request['hub_url'], data=args)
            assert response.status_code == 202
        except requests.exceptions.RequestException as e:
            raise SubscriberError(INVALID_HUB_URL) from e
        except AssertionError as old_err:
            err = SubscriberError("Hub error - %s: %s" % (response.status_code,
                                                          response.content))
            raise err from old_err
        return callback_id

    def safe_post_request(self, url, **opts):
        if not is_secure(url):
            https_url = 'https' + url[len('http'):]
            with contextlib.suppress(requests.exceptions.RequestException):
                return request_url(self.config, 'POST', https_url, **opts)
        return request_url(self.config, 'POST', url, **opts)

    def unsubscribe(self, callback_id):
        """Ask the hub to cancel the subscription for callback_id, then delete
        it from the local database if successful.

        """
        request = self.get_active_subscription(callback_id)
        request['mode'] = 'unsubscribe'
        self.subscribe_impl(callback_id, **request)

    def get_active_subscription(self, callback_id):
        try:
            subscription = self.storage[callback_id]
        except KeyError as e:
            raise SubscriberError(NOT_FOUND + callback_id)
        else:
            return subscription

    def renew(self, callback_id):
        """Renew the subscription given by callback_id with the hub. Note that
        this should work even when the subscription has expired.

        """
        return self.subscribe_impl(callback_id,
                                   **self.get_active_subscription(callback_id))

    def renew_close_to_expiration(self, margin_in_seconds=A_DAY):
        """Automatically renew subscriptions that are close to expiring, or
        have already expired. margin_in_seconds determines if a subscription is
        in fact close to expiring. By default, said margin is set to be a
        single day (24 hours).

        This is a long-running method for any non-trivial usage of the
        subscriber module, as renewal requires several http requests, and
        subscriptions are processed serially. Because of that, it is
        recommended to run this method in a celery task.

        """
        subscriptions = self.storage.close_to_expiration(margin_in_seconds)
        for subscription in subscriptions:
            try:
                self.subscribe_impl(**subscription)
            except SubscriberError as e:
                warn(RENEW_FAILURE % (subscription['topic_url'],
                                      subscription['callback_id']), e)

    def cleanup(self):
        self.temp_storage.cleanup()


def is_secure(url):
    return url.startswith('https://')


def add_secret_to_args(args, request, hub_is_secure):
    # auto set secret (if safe to do so, the user didn't provide a secret,
    # and the functionality is not disabled)
    auto_set_secret = current_app.config.get('AUTO_SET_SECRET', True)
    if hub_is_secure and auto_set_secret:
        request.setdefault('secret', uuid4())
    else:
        request.setdefault('secret')

    if request['secret']:
        # check the invariant for using secrets
        if not hub_is_secure:
            raise SubscriberError(NO_SECRET_WITH_HTTP)
        if secret_too_big(request['secret']):
            raise SubscriberError("Secret is too big.")
        args['hub.secret'] = request['secret']
