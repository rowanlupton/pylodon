from flask import current_app


class EventMixin:
    def __init__(self):
        self.listeners = set()
        self.error_handlers = set()
        self.success_handlers = set()

        @self.add_listener
        def on_notification(topic_url, callback_id, body):
            current_app.logger.debug('(%s, %s) updated', topic_url,
                                     callback_id)

        @self.add_error_handler
        def on_error(*args):
            current_app.logger.debug("(%s, %s) registration failed: %s", *args)

        @self.add_success_handler
        def on_success(*args):
            current_app.logger.debug("(%s, %s) %s succeeded", *args)

    def add_listener(self, f):
        self.listeners.add(f)

    def add_error_handler(self, f):
        self.error_handlers.add(f)

    def add_success_handler(self, f):
        self.success_handlers.add(f)

    def call_all(self, type, *args):
        for handler in getattr(self, type):
            handler(*args)
