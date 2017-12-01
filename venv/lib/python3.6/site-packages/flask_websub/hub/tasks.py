import requests

import base64
import random

from ..utils import get_content, calculate_hmac, request_url, warn, uuid4
from ..errors import NotificationError

__all__ = ('send_change_notification', 'make_request_retrying', 'subscribe',
           'unsubscribe')

INVALID_LINK = "The Link header should contain both 'self' and 'hub' urls"
NO_UPDATED_CONTENT = "Cannot get latest content from topic URL"
INTENT_UNVERIFIED = "Cannot verify subscriber intent - %s: %s"


# standalone tasks
def send_change_notification(hub, topic_url, updated_content=None):
    """7. Content Distribution"""

    if updated_content:
        body = base64.b64decode(updated_content['content'])
    else:
        body, updated_content = get_new_content(hub.config, topic_url)
    b64_body = updated_content['content']

    headers = updated_content['headers']
    link_header = headers.get('Link', '')
    if 'rel="hub"' not in link_header or 'rel="self"' not in link_header:
        raise NotificationError(INVALID_LINK)

    for callback_url, secret in hub.storage.get_callbacks(topic_url):
        schedule_request(hub, topic_url, callback_url, secret, body, b64_body,
                         headers)


def get_new_content(config, topic_url):
    try:
        response = get_content(config, topic_url)
    except requests.exceptions.RequestException as e:
        raise NotificationError(NO_UPDATED_CONTENT) from e
    else:
        return response.content, {
            'headers': response.headers,
            'content': base64.b64encode(response.content).decode('ascii'),
        }


def schedule_request(hub, topic_url, callback_url, secret, body, encoded_body,
                     headers):
    specific_headers = dict(headers)
    if secret:
        # 7.1 Authenticated Content Distribution
        #
        # Default to the strongest algorithm currently in the spec. Better
        # safe than sorry.
        algo = hub.config.get('SIGNATURE_ALGORITHM', 'sha512')
        hmac = calculate_hmac(algo, secret, body)
        specific_headers['X-Hub-Signature'] = algo + '=' + hmac
    hub.make_request_retrying.delay(topic_url, callback_url, specific_headers,
                                    encoded_body)


# the next task is not meant to be user-facing
def make_request_retrying(hub, self, topic_url, callback, headers, b64_body):
    # retry for about an hour by default (enter in the formula & divide by 2
    # due to jitter)
    # https://www.awsarchitectureblog.com/2015/03/backoff.html
    # See also hub/__init__.py for the amount of retry attempts
    backoff_base = hub.config.get('BACKOFF_BASE', 8.0)

    body = base64.b64decode(b64_body)
    try:
        resp = request_url(hub.config, 'POST', callback, headers=headers,
                           data=body)
        assert 200 <= resp.status_code < 300 or resp.status_code == 410
    except (requests.exceptions.RequestException, AssertionError) as e:
        warn("Notification failed", e)
        countdown = random.uniform(0, backoff_base * 2 ** self.request.retries)
        self.retry(countdown=countdown)
    else:
        if resp.status_code == 410:  # 'Gone': send no further notifications
            del hub.storage[topic_url, callback]


# route helpers (for internal use only)
def subscribe(hub, callback_url, topic_url, lease_seconds, secret,
              endpoint_hook_data):
    """5.2 Subscription Validation"""

    for validate in hub.validators:
        error = validate(callback_url, topic_url, lease_seconds, secret,
                         endpoint_hook_data)
        if error:
            send_denied(hub, callback_url, topic_url, error)
            return

    if intent_verified(hub, callback_url, 'subscribe', topic_url,
                       lease_seconds):
        hub.storage[topic_url, callback_url] = {
            'lease_seconds': lease_seconds,
            'secret': secret,
        }


def send_denied(hub, callback_url, topic_url, error):
    try:
        request_url(hub.config, 'GET', callback_url, params={
            'hub.mode': 'denied',
            'hub.topic': topic_url,
            'hub.reason': error,
        })
    except requests.exceptions.RequestException as e:
        warn("Could not send subscription validation result", e)


def intent_verified(hub, callback_url, mode, topic_url, lease_seconds):
    """ 5.3 Hub Verifies Intent of the Subscriber"""

    challenge = uuid4()
    params = {
        'hub.mode': mode,
        'hub.topic': topic_url,
        'hub.challenge': challenge,
        'hub.lease_seconds': lease_seconds,
    }
    try:
        response = request_url(hub.config, 'GET', callback_url, params=params)
        assert response.status_code == 200 and response.text == challenge
    except requests.exceptions.RequestException as e:
        warn("Cannot verify subscriber intent", e)
    except AssertionError as e:
        warn(INTENT_UNVERIFIED % (response.status_code, response.content), e)
    else:
        return True
    return False


def unsubscribe(hub, callback_url, topic_url, lease_seconds):
    # we could check here if the subscription actually exists, but that would
    # slow down the common case and just be more work.
    if intent_verified(hub, callback_url, 'unsubscribe', topic_url,
                       lease_seconds):
        del hub.storage[topic_url, callback_url]
