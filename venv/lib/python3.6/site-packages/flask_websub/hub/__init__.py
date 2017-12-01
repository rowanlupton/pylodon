import functools
import itertools

from .blueprint import build_blueprint, A_DAY
from .tasks import make_request_retrying, send_change_notification, \
                   subscribe, unsubscribe
from .storage import SQLite3HubStorage

__all__ = ('Hub', 'SQLite3HubStorage')


class Hub:
    """This is the API to the hub package. The constructor requires a storage
    object, and also accepts a couple of optional configuration values (the
    defaults are shown as well):

    - BACKOFF_BASE=8.0: When a hub URL cannot be reached, exponential backoff
      is used to control retrying. This parameter scales the whole process.
      Lowering it means trying more frequently, but also for a shorter time.
      Highering it means the reverse.
    - MAX_ATTEMPTS=10: The amount of attempts the retrying process makes.
    - PUBLISH_SUPPORTED=False: makes it possible to do a POST request to the
      hub endpoint with mode=publish. This is nice for testing, but as it does
      no input validation, you should not leave this enabled in production.
    - SIGNATURE_ALGORITHM='sha512': The algorithm to sign a content
      notification body with. Other possible values are sha1, sha256 and
      sha384.
    - REQUEST_TIMEOUT=3: Specifies how long to wait before considering a
      request to have failed.
    - HUB_MIN_LEASE_SECONDS: The minimal lease_seconds value the hub will
      accept
    - HUB_DEFAULT_LEASE_SECONDS: The lease_seconds value the hub will use if
      the subscriber does not have a preference
    - HUB_MAX_LEASE_SECONDS: The maximum lease_seconds value the hub will
      accept

    You can pass in a celery object too, or do that later using init_celery. It
    is required to do so before actually using the hub, though.

    User-facing properties have doc strings. Other properties should be
    considered implementation details.

    """
    counter = itertools.count()

    def __init__(self, storage, celery=None, **config):
        self.validators = []
        self.storage = storage
        self.config = config
        if celery:
            self.init_celery(celery)

    def endpoint_hook(self):
        """Override this method to hook into the endpoint handling. Anything
        this method returns will be forwarded to validation functions when
        subscribing.

        """

    def build_blueprint(hub, url_prefix=''):
        """Build a blueprint containing a Flask route that is the hub endpoint.

        """
        return build_blueprint(hub, url_prefix)

    def init_celery(self, celery):
        """Registers the celery tasks on the hub object."""

        count = next(self.counter)

        def task_with_hub(f, **opts):
            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                return f(self, *args, **kwargs)
            # Make sure newer instances don't overwride older ones.
            wrapper.__name__ = wrapper.__name__ + '_' + str(count)
            return celery.task(**opts)(wrapper)

        # tasks for internal use:
        self.subscribe = task_with_hub(subscribe)
        self.unsubscribe = task_with_hub(unsubscribe)

        max_attempts = self.config.get('MAX_ATTEMPTS', 10)
        make_req = task_with_hub(make_request_retrying, bind=True,
                                 max_retries=max_attempts)
        self.make_request_retrying = make_req

        # user facing tasks:
        self.send_change_notification = task_with_hub(send_change_notification)
        self.send_change_notification.__doc__ = """
        Allows you to notify subscribers of a change to a `topic_url`. This
        is a celery task, so you probably will actually want to call
        hub.send_change_notification.delay(topic_url, updated_content). The
        last argument is optional. If passed in, it should be an object with
        two properties: `headers` (dict-like), and `content` (a byte string).
        If left out, the updated content will be fetched from the topic url
        directly.

        """.lstrip()

        @task_with_hub
        def cleanup(hub):
            """Removes any expired subscriptions from the backing data store.
            It takes no arguments, and is a celery task.

            """
            self.storage.cleanup_expired_subscriptions()
        self.cleanup_expired_subscriptions = cleanup

        def schedule_cleanup(every_x_seconds=A_DAY):
            """schedule_cleanup(every_x_seconds=A_DAY): schedules the celery
            task `cleanup_expired_subscriptions` as a recurring event, the
            frequency of which is determined by its parameter. This is not a
            celery task itself (as the cleanup is only scheduled), and is a
            convenience function.

            """
            celery.add_periodic_task(every_x_seconds,
                                     self.cleanup_expired_subscriptions.s())
        self.schedule_cleanup = schedule_cleanup

    def register_validator(self, f):
        """Register `f` as a validation function for subscription requests. It
        gets a callback_url and topic_url as its arguments, and should return
        None if the validation succeeded, or a string describing the problem
        otherwise.

        """
        self.validators.append(f)
