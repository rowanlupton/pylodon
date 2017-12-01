import abc

from ..utils import SQLite3StorageMixin, warn

RACE_CONDITION = "WerkzeugCacheTempSubscriberStorage race condition."


class SQLite3SubscriberStorageBase(SQLite3StorageMixin):
    def __init__(self, path):
        self.TABLE_SETUP_SQL = """
        create table if not exists {}(
            callback_id text primary key,
            mode text not null,
            topic_url text not null,
            hub_url text not null,
            secret text,
            lease_seconds integer,
            expiration_time integer not null
        )
        """.format(self.TABLE_NAME)

        self.SETITEM_SQL = """
        insert or replace into {}(callback_id, mode, topic_url, hub_url,
                                  secret, lease_seconds, expiration_time)
        values(?, ?, ?, ?, ?, ?, ? + strftime('%s', 'now'))
        """.format(self.TABLE_NAME)

        self.GETITEM_SQL = """
        select mode, topic_url, hub_url, secret, lease_seconds from {}
        where callback_id=? and expiration_time > strftime('%s', 'now');
        """.format(self.TABLE_NAME)

        self.DELITEM_SQL = """
        delete from {} where callback_id=?
        """.format(self.TABLE_NAME)

        super().__init__(path)


# temp storage

class AbstractTempSubscriberStorage(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __setitem__(self, callback_id, subscription_request):
        """Store a new subscription request under the key callback_id. A
        subscription request is a dict-like object with the following keys:

        - mode
        - topic_url
        - hub_url
        - secret
        - lease_seconds
        - timeout: after this amount of seconds, the request itself does no
          longer have to be stored.

        """

    @abc.abstractmethod
    def pop(self, callback_id):
        """Get a subscription request as stored by __setitem__, return it, and
        remove the request from the store. Make sure the request has not
        expired!

        If there is no value for callback_id, raise a KeyError.

        """

    def cleanup(self):
        """Remove any expired subscription requests from the store. If your
        backend handles this automatically, there is no need to override this
        method.

        """


class WerkzeugCacheTempSubscriberStorage(AbstractTempSubscriberStorage):
    def __init__(self, cache):
        """Cache should share the API of werkzeug.contrib.cache.BaseCache"""

        self.cache = cache

    def __setitem__(self, callback_id, subscription_request):
        request = dict(subscription_request)  # clone, as we're going to modify
        self.cache.set(callback_id, request, timeout=request.pop('timeout'))

    def pop(self, callback_id):
        # technically, a race condition could occur here. But it would only
        # occur if a callback_id is in use by multiple hubs. In that case,
        # we have bigger problems.
        result = self.cache.get(callback_id)
        delete_success = self.cache.delete(callback_id)
        if result:
            if not delete_success:
                warn(RACE_CONDITION)
            return result
        raise KeyError(callback_id)


class SQLite3TempSubscriberStorage(AbstractTempSubscriberStorage,
                                   SQLite3SubscriberStorageBase):
    TABLE_NAME = 'subscriber_temp'
    CLEANUP_SQL = """
    delete from subscriber_temp where expiration_time > strftime('%s', 'now')
    """

    def pop(self, callback_id):
        with self.conn as connection:
            cursor = connection.execute(self.GETITEM_SQL, (callback_id,))
            result = cursor.fetchone()
            connection.execute(self.DELITEM_SQL, (callback_id,))
            if result:
                return dict(result)
            raise KeyError(callback_id)

    def __setitem__(self, callback_id, request):
        with self.conn as connection:
            connection.execute(self.SETITEM_SQL, (callback_id,
                                                  request['mode'],
                                                  request['topic_url'],
                                                  request['hub_url'],
                                                  request['secret'],
                                                  request['lease_seconds'],
                                                  request['timeout']))

    def cleanup(self):
        with self.conn as connection:
            connection.execute(self.CLEANUP_SQL)


class AbstractSubscriberStorage(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def __getitem__(self, callback_id):
        """Get a subscription by its callback_id, which is a dict-like object
        with the following keys:

        - mode
        - topic_url
        - hub_url
        - secret
        - lease_seconds

        """

    @abc.abstractmethod
    def __delitem__(self, callback_id):
        """Delete an object by its callback_id"""

    @abc.abstractmethod
    def __setitem__(self, callback_id, subscription):
        """Store a new subscription under the key callback_id. Note that a
        subscription should disappear from any queries after lease_seconds has
        passed from the moment of storage on, with the exception of
        close_to_expiration.

        """

    @abc.abstractmethod
    def close_to_expiration(self, margin_in_seconds):
        """Return an iterator of subscriptions that are near (or already past)
        their expiration time. margin_in_seconds specifies what 'near' is.

        Note that the key 'callback_id' needs to be included in the resulting
        object as well!

        """


class SQLite3SubscriberStorage(AbstractSubscriberStorage,
                               SQLite3SubscriberStorageBase):
    TABLE_NAME = 'subscriber'
    CLOSE_TO_EXPIRATION_SQL = """
    select callback_id, mode, topic_url, hub_url, secret, lease_seconds
    from subscriber where expiration_time < strftime('%s', 'now') + ?
    """

    def __getitem__(self, callback_id):
        cursor = self.conn.execute(self.GETITEM_SQL, (callback_id,))
        result = cursor.fetchone()
        if result:
            return dict(result)
        raise KeyError(callback_id)

    def __delitem__(self, callback_id):
        with self.conn as connection:
            connection.execute(self.DELITEM_SQL, (callback_id,))

    def __setitem__(self, callback_id, subscription):
        with self.conn as conn:
            conn.execute(self.SETITEM_SQL, (callback_id,
                                            subscription['mode'],
                                            subscription['topic_url'],
                                            subscription['hub_url'],
                                            subscription['secret'],
                                            subscription['lease_seconds'],
                                            subscription['lease_seconds']))

    def close_to_expiration(self, margin_in_seconds):
        args = (margin_in_seconds,)
        return iter(self.conn.execute(self.CLOSE_TO_EXPIRATION_SQL, args))
