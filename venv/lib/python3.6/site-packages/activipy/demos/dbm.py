## Activipy --- ActivityStreams 2.0 implementation and validator for Python
## Copyright © 2015 Christopher Allan Webber <cwebber@dustycloud.org>
##
## This file is part of Activipy, which is GPLv3+ or Apache v2, your option
## (see COPYING); since that means effectively Apache v2 here's those headers
##
## Apache v2 header:
##   Licensed under the Apache License, Version 2.0 (the "License");
##   you may not use this file except in compliance with the License.
##   You may obtain a copy of the License at
##
##       http://www.apache.org/licenses/LICENSE-2.0
##
##   Unless required by applicable law or agreed to in writing, software
##   distributed under the License is distributed on an "AS IS" BASIS,
##   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##   See the License for the specific language governing permissions and
##   limitations under the License.

import json

import dbm

from activipy import core, vocab


class JsonDBM(object):
    """
    json wrapper around a gdbm database
    """
    def __init__(self, db):
        self.db = db

    def __getitem__(self, key):
        return json.loads(self.db[key.encode('utf-8')].decode('utf-8'))

    def __setitem__(self, key, value):
        self.db[key.encode('utf-8')] = json.dumps(value)

    def __delitem__(self, key):
        del self.db[key.encode('utf-8')]

    def __contains__(self, key):
        return key in self.db

    @classmethod
    def open(cls, filename):
        return cls(dbm.open(filename, 'c'))

    def close(self):
        self.db.close()

    def get(self, key, default=None):
        if key in self.db:
            return self[key]
        else:
            return default

    def fetch_asobj(self, env):
        return core.ASObj(self[id], env)

# Each of these returns the full object inserted into dbm

def dbm_fetch(id, db, env):
    return core.ASObj(db[id], env)

def dbm_save(asobj, db):
    assert asobj.id is not None
    new_val = asobj.json()
    db[asobj.id] = new_val
    return new_val

def dbm_delete(asobj, db):
    assert asobj.id is not None
    del db[asobj.id]


dbm_save_method = core.MethodId(
    "save", "Save object to the DBM store.",
    core.handle_one)
dbm_delete_method = core.MethodId(
    "delete", "Delete object from the DBM store.",
    core.handle_one)

DbmEnv = core.Environment(
    vocabs=[vocab.CoreVocab],
    methods={
        (dbm_save_method, vocab.Object): dbm_save,
        (dbm_delete_method, vocab.Object): dbm_delete},
    shortids=core.shortids_from_vocab(vocab.CoreVocab),
    c_accessors=core.shortids_from_vocab(vocab.CoreVocab))


def dbm_activity_normalized_save(asobj, db):
    assert asobj.id is not None
    as_json = asobj.json()

    def maybe_normalize(key):
        val = as_json.get(key)
        # Skip if not a dictionary with a "@type"
        if not isinstance(val, dict) or not "@type" in val:
            return

        val_asobj = core.ASObj(val, asobj.env)
        # yup, time to normalize
        if asobj.env.is_astype(val_asobj, vocab.Object, inherit=True):
            # If there's no id, then okay, don't normalize
            if val_asobj.id is None:
                return

            if val_asobj.id not in db:
                # save to the database
                asobj.env.asobj_run_method(val_asobj, dbm_save_method, db)

            # and set the key to be the .id
            as_json[key] = val_asobj.id

    maybe_normalize("actor")
    maybe_normalize("object")
    maybe_normalize("target")
    db[asobj.id] = as_json
    return as_json


dbm_denormalize_method = core.MethodId(
    "denormalize", "Expand out an activitystreams object recursively",
    # @@: Should this be a handle_fold?
    core.handle_one)


def dbm_denormalize_object(asobj, db):
    # For now, on any standard object, just return that as-is
    return asobj


def dbm_denormalize_activity(asobj, db):
    as_json = asobj.json()

    def maybe_denormalize(key):
        val = as_json.get(key)
        # If there's no specific val,
        # it's not a string, or it's not in the database,
        # just leave it!
        if val is None or not isinstance(val, str) or val not in db:
            return

        # Otherwise, looks like that value *is* in the database... hey!
        # Let's pull it out and set it as the key.
        as_json[key] = db[val]

    maybe_denormalize("actor")
    maybe_denormalize("object")
    maybe_denormalize("target")
    return core.ASObj(as_json, asobj.env)


DbmNormalizedEnv = core.Environment(
    vocabs=[vocab.CoreVocab],
    methods={
        (dbm_save_method, vocab.Object): dbm_save,
        (dbm_save_method, vocab.Activity): dbm_activity_normalized_save,
        (dbm_delete_method, vocab.Object): dbm_delete,
        (dbm_denormalize_method, vocab.Object): dbm_denormalize_object,
        (dbm_denormalize_method, vocab.Activity): dbm_denormalize_activity},
    shortids=core.shortids_from_vocab(vocab.CoreVocab),
    c_accessors=core.shortids_from_vocab(vocab.CoreVocab))


def dbm_fetch_denormalized(id, db, env):
    """
    Fetch a fully denormalized ASObj from the database.
    """
    return env.asobj_run_method(
        dbm_fetch(id, db, env),
        dbm_denormalize_method, db)
