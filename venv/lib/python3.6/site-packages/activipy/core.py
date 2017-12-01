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

from pkg_resources import resource_filename
import copy
import json

from pyld import jsonld


# The actual instances of these are defined in vocab.py

class ASType(object):
    """
    A @type than an ActivityStreams object might take on.

    BTW, you might wonder why this isn't using python class heirarchies
    as an abstraction.  The reason is simple: ActivityStreams objects
    can have multiple types listed under @type.  So our inheritance
    model is a bit different than python's.
    """
    def __init__(self, id_uri, parents, id_short=None, notes=None):
        self.id_uri = id_uri
        self.parents = parents
        self.id_short = id_short
        self.notes = notes

        self._inheritance = None

    def validate(self, asobj):
        validator = self.methods.get("validate")
        if validator is not None:
            validator(asobj)

    def __repr__(self):
        return "<ASType %s>" % (self.id_short or self.id_uri)

    # TODO: Use a generic memoizer?
    @property
    def inheritance_chain(self):
        # memoization
        if self._inheritance is None:
            self._inheritance = astype_inheritance_list(self)

        return self._inheritance

    def __call__(self, id=None, env=None, **kwargs):
        # @@: Is this okay?  Kinda bold!
        if env is None:
            from activipy import vocab
            env = vocab.BasicEnv

        if self in env.shortids_reversemap:
            type_val = env.shortids_reversemap[self]
        else:
            type_val = self.id_uri

        jsobj = {"@type": type_val}
        jsobj.update(kwargs)
        if id:
            jsobj["@id"] = id

        if env:
            return ASObj(jsobj, env=env)
        else:
            return ASObj(jsobj)


def astype_inheritance_list(*astypes):
    """
    Gather the inheritance list for an ASType or multiple ASTypes

    We need this because unlike w/ Python classes, an individual
    ASObj can have composite types.
    """
    def traverse(astype, family):
        family.append(astype)
        for parent in astype.parents:
            traverse(parent, family)

        return family

    # not deduped at this point
    family = []
    for astype in astypes:
        family = traverse(astype, family)

    # okay, dedupe here, only keep the oldest instance of each
    family.reverse()
    deduped_family = []
    for member in family:
        if member not in deduped_family:
            deduped_family.append(member)

    deduped_family.reverse()
    return deduped_family


class ASVocab(object):
    """
    Mapping of known type IDs to ASTypes

    TODO: Maybe this should include the appropriate context
      it's working within?
    """
    def __init__(self, vocabs):
        self.vocab_map = self._map_vocabs(vocabs)

    def _map_vocabs(self, vocabs):
        return {
            type.id_uri: type
            for type in vocabs}


# TODO: Add this one by default
AS2_CONTEXT_FILE = resource_filename(
    'activipy', 'activitystreams2-context.jsonld')
AS2_CONTEXT = json.loads(open(AS2_CONTEXT_FILE, 'r').read())
AS2_CONTEXT_URI = (
    "http://www.w3.org/TR/activitystreams-core/activitystreams2-context.jsonld")
AS2_DEFAULT_URL_MAP = {
    AS2_CONTEXT_URI: AS2_CONTEXT}

# Once things are cached, json-ld expansion seems to happen at about
# 1250 douments / second on my laptop

def make_simple_loader(url_map, load_unknown_urls=True,
                       cache_externally_loaded=True):
    def _make_context(url, doc):
        return {
            "contextUrl": None,
            "documentUrl": url,
            "document": doc}

    # Wrap in the structure that's expected to come back from the
    # documentLoader
    _pre_url_map = {}
    _pre_url_map.update(AS2_DEFAULT_URL_MAP)
    _pre_url_map.update(url_map)
    _url_map = {
        url: _make_context(url, doc)
        for url, doc in _pre_url_map.items()}

    def loader(url):
        if url in _url_map:
            return _url_map[url]
        elif load_unknown_urls:
            doc = jsonld.load_document(url)
            # @@: Is this optimization safe in all cases?
            if isinstance(doc["document"], str):
                doc["document"] = json.loads(doc["document"])
            if cache_externally_loaded:
                _url_map[url] = doc
            return doc
        else:
            raise jsonld.JsonLdError(
                "url not found and loader set to not load unknown URLs.",
                {'url': url})

    return loader

default_loader = make_simple_loader({})

# TODO: This was a good early in-comments braindump; now move to the
# documentation and restructure!

# So, questions for ourselves.  What is this, if not merely a json
# object?  After all, an ActivityStreams object can be represented as
# "just JSON", and be done with it.  So what's *useful*?
#
# Here are some potentially useful properties:
#  - Expanded json-ld form
#  - Extracted types
#    - As short forms
#    - As expanded / unambiguous URIs (see json-ld)
#    - As ASType objects (where possible)
#  - Validation
#  - Lookup of what a property key "means"
#    (checking against activitystreams vocabulary)
#  - key-value access, including fetching any nested activitystreams
#    objects as ASObj types
#  - json serialization to string
#
# Of all the above, it would be nice not to have to repeat these
# operations.  If we've done it once, that should be good enough
# forever... in other words, memoization.  But memoization means
# that the object should be immutable.
#
# ... but maybe ASObj objects *should* be immutable.
# This means we copy.deepcopy() on our way in, and if users want
# to change things, they either make a new ASObj or get back
# entirely new ASObj objects.
#
# I like this idea...

class ASObj(object):
    """
    The general ActivityStreams object that a user will work with
    """
    def __init__(self, jsobj, env=None):
        if not env:
            from activipy import vocab
            env = vocab.BasicEnv
        self.env = env

        self.__jsobj = deepcopy_jsobj_in(jsobj, env)
        assert (isinstance(self.__jsobj.get("@type"), str) or
                isinstance(self.__jsobj.get("@type"), list))

        self.m = self.env._build_m_map(self)

    def __getitem__(self, key):
        val = self.__jsobj[key]
        if isinstance(val, dict) and "@type" in val:
            return ASObj(val, self.env)
        else:
            return deepcopy_jsobj_out(val, env=self.env)

    # META TODO: Convert some @property here to @memoized_property
    @property
    def types(self):
        type_attr = self["@type"]
        if isinstance(self["@type"], list):
            return type_attr
        else:
            return [type_attr]

    @property
    def types_expanded(self):
        return copy.deepcopy(self.__expanded()[0]["@type"])

    # TODO: Memoize
    @property
    def types_astype(self):
        return self.env.asobj_astypes(self)

    # TODO: Memoize
    @property
    def types_inheritance(self):
        return self.env.asobj_astype_inheritance(self)

    # Don't memoize this, users might mutate
    def json(self):
        return copy.deepcopy(self.__jsobj)

    # TODO: Memoize
    def json_str(self):
        return json.dumps(self.json())

    # TODO Memoize
    def __expanded(self):
        if self.env.document_loader:
            document_loader = self.env.document_loader
        else:
            document_loader = default_loader

        options = {"expandContext": self.env.implied_context}
        if document_loader:
            options["documentLoader"] = document_loader

        return jsonld.expand(self.__jsobj, options)

    def expanded(self):
        """
        Note: this produces a copy of the object returned, so consumers
          of this method may want to keep a copy of its result
          rather than calling over and over.
        """
        return copy.deepcopy(self.__expanded())

    # TODO: Memoize
    def expanded_str(self):
        return json.dumps(self.expanded())

    @property
    def id(self):
        return self.__jsobj.get("@id")

    def __repr__(self):
        if self.id:
            return "<ASObj %s \"%s\">" % (
                ", ".join(self.types),
                self.id)
        else:
            return "<ASObj %s>" % ", ".join(self.types)


def deepcopy_jsobj_base(jsobj, env, going_in=True):
    """
    Perform a deep copy of a JSON style object
    """
    going_out = not going_in

    def add_context(this_dict):
        if env.extra_context is not None:
            this_dict["@context"] = env.extra_context

    def remove_context(this_dict):
        if "@context" in this_dict:
            del this_dict["@context"]
        return this_dict

    def copy_asobj(asobj):
        if going_in:
            return remove_context(asobj.json())
        else:
            return asobj

    def copy_dict(this_dict):
        # Looks like an ASObj
        if going_out and "@type" in this_dict:
            return ASObj(this_dict, env)

        # Otherwise, just recursively copy the dict
        new_dict = {}
        for key, val in this_dict.items():
            new_dict[key] = copy_main(val)
        return new_dict

    def copy_list(this_list):
        new_list = []
        for item in this_list:
            new_list.append(copy_main(item))
        return new_list

    def copy_main(jsobj):
        if isinstance(jsobj, dict):
            return copy_dict(jsobj)
        elif isinstance(jsobj, ASObj):
            return copy_asobj(jsobj)
        elif isinstance(jsobj, list):
            return copy_list(jsobj)
        else:
            # All other JSON type objects are immutable,
            # just copy them down.
            # @@: We could provide validation that it's
            #   a valid json object here but that seems like
            #   it would bring unnecessary performance penalties.
            return jsobj

    if going_in:
        # Should be a dictionary or ASObj on the way in for this
        assert isinstance(jsobj, dict) or isinstance(jsobj, ASObj)

    final_json = copy_main(jsobj)

    if going_in:
        add_context(final_json)

    return final_json


def deepcopy_jsobj_in(jsobj, env):
    return deepcopy_jsobj_base(jsobj, env, going_in=True)

def deepcopy_jsobj_out(jsobj, env):
    return deepcopy_jsobj_base(jsobj, env, going_in=False)


# @@: Maybe rename to MethodSpec?
class MethodId(object):
    # TODO: fill in
    """
    A method identifier
    """
    def __init__(self, name, description, handler):
        self.name = name
        self.description = description
        self.handler = handler

    def __repr__(self):
        return "<MethodId %s>" % self.name


class NoMethodFound(Exception): pass

def throw_no_method_error(asobj):
    raise NoMethodFound("Could not find a method for type: %s" % (
        ", ".join(asobj.types)))

def handle_one(astype_methods, asobj, _fallback=throw_no_method_error):
    if len(astype_methods) == 0:
        _fallback(asobj)

    def func(*args, **kwargs):
        method, astype = astype_methods[0]
        return method(asobj, *args, **kwargs)
    return func


def handle_map(astype_methods, asobj):
    def func(*args, **kwargs):
        return [method(asobj, *args, **kwargs)
                for method, astype in astype_methods]
    return func


class HaltIteration(object):
    def __init__(self, val):
        self.val = val


def handle_fold(astype_methods, asobj):
    def func(initial=None, *args, **kwargs):
        val = initial
        for method, astype in astype_methods:
            # @@: Not sure if asobj or val coming first is a better interface...
            val = method(asobj, val, *args, **kwargs)
            # Provide a way to break out of the loop early...?
            # @@: Is this a good idea, or even useful for anything?
            if isinstance(val, HaltIteration):
                val = val.val
                break
        return val
    return func


# TODO
# @@: Can this be just an @property on Environment?
class AttrMapper(object):
    def __init__(self, attrib_map):
        for key, val in attrib_map.items():
            setattr(self, key, val)

class TypeConstructor(object):
    def __init__(self, astype, env):
        self.astype = astype
        self.__env = env

    def __call__(self, *args, **kwargs):
        return self.astype(env=self.__env, *args, **kwargs)

    def __repr__(self):
        return "<TypeConstructor for %s>" % self.astype.__repr__()


class EnvironmentMismatch(Exception):
    """
    Raised when an ASObj calls a method through an Environment
    but does not have that environment bound to itself.
    """
    pass


class Environment(object):
    """
    An environment to collect vocabularies and provide
    methods for activitystream types
    """
    implied_context = AS2_CONTEXT_URI

    def __init__(self, vocabs=None, methods=None,
                 # not ideal, I'd rather somehow load something
                 # that uses the vocabs as passed in, but that
                 # introduces its own complexities
                 shortids=None, c_accessors=None,
                 extra_context=None,
                 document_loader=default_loader):
        self.vocabs = vocabs or []
        self.methods = methods or {}
        # @@: Should we make all short ids mandatorily contain
        #   the base schema?
        self.shortids = shortids or {}
        self.shortids_reversemap = {
            val: key for key, val in self.shortids.items()}
        self.extra_context = extra_context
        self.document_loader = document_loader
        self.c = self.__build_c_accessors(c_accessors or {})
        self.m = self._build_m_map()

        self.uri_map = self.__build_uri_map()

    def __build_c_accessors(self, c_accessors):
        return AttrMapper(
            {name: TypeConstructor(astype, self)
             for name, astype in c_accessors.items()})

    def _build_m_map(self, asobj=None):
        def make_method_dispatcher(method_id):
            def method_dispatcher(asobj, *args, **kwargs):
                method = self.asobj_get_method(asobj, method_id)
                return method(*args, **kwargs)
            if asobj is None:
                return method_dispatcher
            else:
                # in this variation, we already know what the
                # asobj is
                def curried_method_dispatcher(*args, **kwargs):
                    return method_dispatcher(asobj, *args, **kwargs)
                return curried_method_dispatcher

        method_ids = set([method_id for (method_id, astype)
                          in self.methods.keys()])
        m_mapping = {
            method_id.name: make_method_dispatcher(method_id)
            for method_id in method_ids}

        return AttrMapper(m_mapping)

    def __build_uri_map(self):
        uri_map = {}
        for vocab in self.vocabs:
            uri_map.update(vocab.vocab_map)

        return uri_map

    def _process_type_simple(self, type_id):
        # Try by short ID (in short IDs marked as acceptable for this)
        if type_id in self.shortids:
            return self.shortids[type_id]

        # Try by URI
        elif type_id in self.uri_map:
            return self.uri_map[type_id]

        else:
            # this would happen anyway, but might as well be explicit
            # about what's happening here in the code flow
            return None

    def asobj_astypes(self, asobj):
        final_types = []
        process_as_jsonld = False
        for type_id in asobj.types:
            processed_type = self._process_type_simple(type_id)
            if processed_type is not None:
                final_types.append(processed_type)
            else:
                # We have to bail out
                process_as_jsonld = True
                break

        # Are there any remaining types to process here?
        if process_as_jsonld:
            # @@: We could do a version of this which didn't
            #   throw away the information we already had,
            #   maybe.  But it would be tricky.
            final_types = []
            asobj_jsonld = asobj.expanded()
            for type_uri in asobj_jsonld[0]["@type"]:
                processed_type = self._process_type_simple(type_uri)
                if processed_type is not None:
                    final_types.append(processed_type)

        return final_types

    def asobj_astype_inheritance(self, asobj):
        return astype_inheritance_list(
            *self.asobj_astypes(asobj))

    def is_astype(self, asobj, astype, inherit=True):
        """
        Check to see if an ASObj is of ASType; check full inheritance chain
        """
        if not isinstance(asobj, ASObj):
            return False

        if inherit:
            return astype in self.asobj_astype_inheritance(asobj)
        else:
            return astype in self.asobj_astypes(asobj)

    # @@: Should we drop the asobj_ from these method names?
    def asobj_get_method(self, asobj, method):
        if asobj.env is not self:
            raise EnvironmentMismatch(
                "ASObj attempted to call method with an Environment "
                "it was not bound to!")

        # get all types for this asobj
        astypes = self.asobj_astype_inheritance(asobj)

        # get a map of all relevant {method_proc: astype}
        return method.handler(
            [(self.methods[(method, astype)], astype)
             for astype in astypes
             if (method, astype) in self.methods],
            asobj)

    def asobj_run_method(self, asobj, method, *args, **kwargs):
        # make note of why arguments make this slightly lossy
        # when passing on; eg, can't use asobj/method in the
        # arguments to this function
        return self.asobj_get_method(asobj, method)(*args, **kwargs)


def shortids_from_vocab(vocab, prefix=None):
    """
    Get a mapping of all short ids to their ASType objects in a vocab

    Useful for mapping shortids to ASType objects!
    """
    def maybe_add_prefix(id_short):
        if prefix:
            return "%s:%s" % (prefix, id_short)
        else:
            return id_short

    return {
        maybe_add_prefix(v.id_short): v
        for v in vocab.vocab_map.values()}


def chain_dicts(*dicts):
    """
    Chain together a series of dictionaries into one
    """
    final_dict = {}
    for this_dict in dicts:
        final_dict.update(this_dict)
    return final_dict
