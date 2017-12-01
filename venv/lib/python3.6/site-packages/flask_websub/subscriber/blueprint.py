from flask import abort, request, Blueprint

import hmac

from ..utils import warn, parse_lease_seconds, calculate_hmac

NOT_FOUND = "Could not found subscription with callback id '%s'"


def build_blueprint(subscriber, url_prefix):
    name = 'websub_callbacks' + url_prefix.replace('/', '_')
    callbacks = Blueprint(name, __name__, url_prefix=url_prefix)

    @callbacks.route('/<callback_id>', methods=['GET'])
    def subscription_confirmation(callback_id):
        mode = get_query_arg('hub.mode')
        try:
            subscription_request = subscriber.temp_storage.pop(callback_id)
        except KeyError as e:
            warn(NOT_FOUND % callback_id, e)
            abort(404)
        if mode == 'denied':
            return subscription_denied(callback_id, subscription_request)
        elif mode in ['subscribe', 'unsubscribe']:
            return confirm_subscription(callback_id, subscription_request)
        else:
            abort(400, "Invalid mode")

    def subscription_denied(callback_id, subscription_request):
        # 5.2 Subscription Validation

        # TODO: support Location header? It's a MAY, but a nice feature. Maybe
        # later, behind a config option.
        reason = request.args.get('hub.reason', 'denied')
        subscriber.call_all('error_handlers',
                            subscription_request['topic_url'], callback_id,
                            reason)
        return "'denied' acknowledged\n"

    def confirm_subscription(callback_id, subscription_request):
        mode = get_query_arg('hub.mode')
        topic_url = get_query_arg('hub.topic')
        if mode != subscription_request['mode']:
            abort(404, "Mode does not match with last request")
        if topic_url != subscription_request['topic_url']:
            abort(404, "Topic url does not match")
        if mode == 'subscribe':
            lease = parse_lease_seconds(get_query_arg('hub.lease_seconds'))
            subscription_request['lease_seconds'] = lease
            # this is the point where the subscription request is turned into
            # a subscription:
            subscriber.storage[callback_id] = subscription_request
        else:  # unsubscribe
            del subscriber.storage[callback_id]
        subscriber.call_all('success_handlers', topic_url, callback_id, mode)
        return get_query_arg('hub.challenge'), 200

    @callbacks.route('/<callback_id>', methods=['POST'])
    def callback(callback_id):
        try:
            subscription = subscriber.storage[callback_id]
        except (KeyError, AssertionError):
            abort(404)
        # 1 MiB by default
        max_body_size = subscriber.config.get('MAX_BODY_SIZE', 1024 * 1024)
        if request.content_length > max_body_size:
            abort(400, "Body too large")
        body = request.get_data()
        if body_is_valid(subscription, body):
            subscriber.call_all('listeners', subscription['topic_url'],
                                callback_id, body)
        return 'Content received\n'

    return name, callbacks


def get_query_arg(name):
    try:
        return request.args[name]
    except KeyError:
        abort(400, "Missing query argument: " + name)


def body_is_valid(subscription, body):
    if not subscription['secret']:
        return True
    try:
        algo, signature = request.headers['X-Hub-Signature'].split('=')
        expected_signature = calculate_hmac(algo, subscription['secret'], body)
    except KeyError as e:
        warn("X-Hub-Signature header expected but not set", e)
    except ValueError as e:
        warn("X-Hub-Signature header is invalid", e)
    except AttributeError as e:
        warn("Invalid algorithm in X-Hub-Signature", e)
    else:
        if hmac.compare_digest(signature, expected_signature):
            return True
    return False
