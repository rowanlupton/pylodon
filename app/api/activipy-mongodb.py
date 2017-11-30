import json
from app import mongo

from activipy import core, vocab

class JsonMongoDB(object):
  """
  json wrapper around a mongo database
  """
  def __init__(self, db):
    self.db = db

  def __getitem__(self, key):
    return self.db.find_one({'id': key.encode('utf-8')}, {'_id': False})

  def __setitem__(self, item):
    self.db.insert_one(json.dumps(item))

  def __delitem__(self, key):
    self.db.remove({'id': key.encode('utf-8')})

  def __contains__(self, key):
    return (self.db.find({'id': key.encode('utf-8')}).count() > 0)

  @classmethod
  def get(self, key, default=None):
  	try:
  		return self.db.find_one({'id': key}, {'_id': False})
    except:
      return default()

  def fetch_asobj(self, env):
		return core.ASObj(self[id], env)


def mongo_fetch(id, db, env):
    return core.ASObj(db[id], env)

def mongo_insert(asobj, db):
    assert asobj.id is not None
    new_val = asobj.json()
    db.insert_one(new_val)
    # db[asobj.id] = new_val
    return new_val

def mongo_remove(asobj, db):
    assert asobj.id is not None
    db.remove({'id': asobj.id})


mongo_insert_method = core.MethodId(
    "insert", "Save object to the MongoDB store.",
    core.handle_one)
mongo_remove_method = core.MethodId(
    "remove", "Delete object from the MongoDB store.",
    core.handle_one)

MongoDBEnv = core.Environment(
    vocabs=[vocab.CoreVocab],
    methods={
        (mongo_insert_method, vocab.Object): mongo_insert,
        (mongo_remove_method, vocab.Object): mongo_remove},
    shortids=core.shortids_from_vocab(vocab.CoreVocab),
    c_accessors=core.shortids_from_vocab(vocab.CoreVocab))


# def mongo_activity_normalized_save(asobj, db):
#     assert asobj.id is not None
#     as_json = asobj.json()

#     def maybe_normalize(key):
#         val = as_json.get(key)
#         # Skip if not a dictionary with a "@type"
#         if not isinstance(val, dict) or not "@type" in val:
#             return

#         val_asobj = core.ASObj(val, asobj.env)
#         # yup, time to normalize
#         if asobj.env.is_astype(val_asobj, vocab.Object, inherit=True):
#             # If there's no id, then okay, don't normalize
#             if val_asobj.id is None:
#                 return

#             if val_asobj.id not in db:
#                 # save to the database
#                 asobj.env.asobj_run_method(val_asobj, dbm_save_method, db)

#             # and set the key to be the .id
#             as_json[key] = val_asobj.id

#     maybe_normalize("actor")
#     maybe_normalize("object")
#     maybe_normalize("target")
#     db[asobj.id] = as_json
#     return as_json


# dbm_denormalize_method = core.MethodId(
#     "denormalize", "Expand out an activitystreams object recursively",
#     # @@: Should this be a handle_fold?
#     core.handle_one)


# def dbm_denormalize_object(asobj, db):
#     # For now, on any standard object, just return that as-is
#     return asobj


# def dbm_denormalize_activity(asobj, db):
#     as_json = asobj.json()

#     def maybe_denormalize(key):
#         val = as_json.get(key)
#         # If there's no specific val,
#         # it's not a string, or it's not in the database,
#         # just leave it!
#         if val is None or not isinstance(val, str) or val not in db:
#             return

#         # Otherwise, looks like that value *is* in the database... hey!
#         # Let's pull it out and set it as the key.
#         as_json[key] = db[val]

#     maybe_denormalize("actor")
#     maybe_denormalize("object")
#     maybe_denormalize("target")
#     return core.ASObj(as_json, asobj.env)


# DbmNormalizedEnv = core.Environment(
#     vocabs=[vocab.CoreVocab],
#     methods={
#         (dbm_save_method, vocab.Object): dbm_save,
#         (dbm_save_method, vocab.Activity): dbm_activity_normalized_save,
#         (dbm_delete_method, vocab.Object): dbm_delete,
#         (dbm_denormalize_method, vocab.Object): dbm_denormalize_object,
#         (dbm_denormalize_method, vocab.Activity): dbm_denormalize_activity},
#     shortids=core.shortids_from_vocab(vocab.CoreVocab),
#     c_accessors=core.shortids_from_vocab(vocab.CoreVocab))


# def dbm_fetch_denormalized(id, db, env):
#     """
#     Fetch a fully denormalized ASObj from the database.
#     """
#     return env.asobj_run_method(
#         dbm_fetch(id, db, env),
# dbm_denormalize_method, db)