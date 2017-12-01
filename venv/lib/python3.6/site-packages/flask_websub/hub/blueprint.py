from flask import Blueprint, abort, request, current_app

from ..utils import parse_lease_seconds, secret_too_big, A_MINUTE, A_DAY

INVALID_MODE = "Invalid hub.mode (should be 'subscribe' or 'unsubscribe'): "

TEN_DAYS = A_DAY * 10
A_MONTH = A_DAY * 31

first_time = True


def build_blueprint(hub, url_prefix):
    global first_time
    if first_time:
        name = 'websub_hub'
        first_time = False
    else:
        name = 'websub_hub' + url_prefix.replace('/', '_')
    hub_blueprint = Blueprint(name, __name__, url_prefix=url_prefix)

    @hub_blueprint.route('', methods=['POST'])
    def endpoint():
        """The hub endpoint. You make a POST request against it to
        subscribe/unsubscribe/publish. Implemented as a blueprint so it can be
        a top-level function, that is hooked into an app object later (by Hub).

        """
        mode = get_form_arg('hub.mode')
        topic_url = get_form_arg('hub.topic')
        if mode in ['subscribe', 'unsubscribe']:
            callback_url = get_form_arg('hub.callback')
        lease_seconds = get_lease_seconds()
        secret = request.form.get('hub.secret')
        if secret and secret_too_big(secret):
            abort(400, "Secret is too big (should be < 200 bytes)")

        publish_supported = current_app.config.get('PUBLISH_SUPPORTED', False)
        endpoint_hook_data = hub.endpoint_hook()
        if mode == 'subscribe':
            hub.subscribe.delay(callback_url, topic_url, lease_seconds, secret,
                                endpoint_hook_data)
        elif mode == 'unsubscribe':
            hub.unsubscribe.delay(callback_url, topic_url, lease_seconds)
        elif mode == 'publish' and publish_supported:
            hub.send_change_notification.delay(topic_url)
        else:
            abort(400, INVALID_MODE + mode)
        return "Request received: %s\n" % mode, 202

    @hub_blueprint.errorhandler(400)
    def handle_bad_request(error):
        return error.description + '\n', 400

    return hub_blueprint


# route helpers
def get_form_arg(name):
    try:
        return request.form[name]
    except KeyError:
        abort(400, "Missing form argument: " + name)


def get_lease_seconds():
    config = current_app.config
    min_lease = config.get('HUB_MIN_LEASE_SECONDS', A_MINUTE)
    # 8.2 Subscriptions specifies a recommended default
    default_lease = config.get('HUB_DEFAULT_LEASE_SECONDS', TEN_DAYS)
    max_lease = config.get('HUB_MAX_LEASE_SECONDS', A_MONTH)
    assert min_lease <= default_lease <= max_lease

    try:
        lease_seconds = parse_lease_seconds(request.form['hub.lease_seconds'])
    except KeyError:
        return default_lease
    else:
        # make sure the user value is within server bounds. If not, force it.
        return min(max(lease_seconds, min_lease), max_lease)
