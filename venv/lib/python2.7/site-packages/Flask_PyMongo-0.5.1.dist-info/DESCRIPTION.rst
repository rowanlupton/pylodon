Flask-PyMongo
-------------

PyMongo support for Flask applications.

Installation
============

Flask-PyMongo is pip-installable:

    pip install Flask-PyMongo

You can install the latest development snapshot like so:

    pip install http://github.com/dcrosta/flask-pymongo/tarball/master#egg=Flask-PyMongo-dev

Upgrading
~~~~~~~~~

- Version 0.2.0 introduced a dependency on PyMongo version 2.4 or later, and
  introduced some potential backwards-breaking changes. Please review the
  `Changelog <http://flask-pymongo.readthedocs.org/en/latest/#history-and-contributors>`_
  carefully before upgrading.
- Version 0.3.0 removed the `ReadPreference
  <http://api.mongodb.org/python/current/api/pymongo/index.html#pymongo.read_preferences.ReadPreference>`_
  redefinitions in ``flask_pymongo``, in favor of using the constants directly
  from `PyMongo <http://api.mongodb.org/python/current/>`_. Please review the
  `Changelog <http://flask-pymongo.readthedocs.org/en/latest/#history-and-contributors>`_
  carefully before upgrading.

Development
===========

Source code is hosted in `GitHub <https://github.com/dcrosta/flask-pymongo>`_
(contributions are welcome!)


