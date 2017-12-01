import abc

from ..utils import SQLite3StorageMixin

__all__ = ('AbstractHubStorage', 'SQLite3HubStorage',)


class AbstractHubStorage(metaclass=abc.ABCMeta):
    """This abstract class formalizes the data model used by a hub.
    Implementations should take into account that methods can be called from
    different threads or even different processes.

    """
    @abc.abstractmethod
    def __delitem__(self, key):
        """A key consists of two components: (topic_url, callback_url).

        If the operation cannot be performed (e.g. because of there not being
        an item matching the key in the database), you may log an error. An
        exception should not be raised, though.

        """

    @abc.abstractmethod
    def __setitem__(self, key, value):
        """For key info, see __delitem__. value is a dict with the following
        properties:

        - expiration_time
        - secret

        """

    @abc.abstractmethod
    def get_callbacks(self, topic_url):
        """A generator function that should return tuples with the following
        values for each item in storage that has a matching topic_url:

        - callback_url
        - secret

        Note that expired objects should not be yielded.

        """

    def cleanup_expired_subscriptions(self):
        """If your storage backend enforces the expiration times, there's
        nothing more to do. If it does not do so by default, you should
        override this method, and remove all expired entries.

        """


class SQLite3HubStorage(AbstractHubStorage, SQLite3StorageMixin):
    TABLE_SETUP_SQL = """
    create table if not exists hub(
        topic_url text not null,
        callback_url text not null,
        secret text,
        expiration_time integer not null,
        primary key (topic_url, callback_url)
    )
    """
    DELITEM_SQL = "delete from hub where topic_url=? and callback_url=?"
    SETITEM_SQL = """
    insert or replace into hub(topic_url, callback_url, expiration_time,
                               secret)
    values (?, ?, strftime('%s', 'now') + ?, ?)
    """
    GET_CALLBACKS_SQL = """
    select callback_url, secret from hub
    where topic_url=? and expiration_time > strftime('%s', 'now')
    """
    CLEANUP_EXPIRED_SUBSCRIPTIONS_SQL = """
    delete from hub where expiration_time <= strftime('%s', 'now')
    """

    def __delitem__(self, key):
        with self.conn as connection:
            connection.execute(self.DELITEM_SQL, key)

    def __setitem__(self, key, value):
        with self.conn as connection:
            connection.execute(self.SETITEM_SQL, key + (value['lease_seconds'],
                                                        value['secret'],))

    def get_callbacks(self, topic_url):
        cursor = self.conn.execute(self.GET_CALLBACKS_SQL, (topic_url,))
        return iter(cursor)

    def cleanup_expired_subscriptions(self):
        with self.conn as connection:
            connection.execute(self.CLEANUP_EXPIRED_SUBSCRIPTIONS_SQL)
