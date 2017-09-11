## Activipy --- ActivityStreams 2.0 implementation and testing for Python
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
##
## In addition, this page copies huge swaths of documentation from the
## ActivityStreams 2.0 Vocabulary document,
##   http://www.w3.org/TR/activitystreams-vocabulary/
##
## Copyright © 2015 Activity Streams Working Group, IBM & W3C® (MIT,
##   ERCIM, Keio, Beihang). W3C liability, trademark and permissive
##   document license rules apply. 
##
## which is released under the
## "W3C Software and Document Notice and License":
## 
##    This work is being provided by the copyright holders under the
##    following license.
##
##    License
##    -------
##    
##    By obtaining and/or copying this work, you (the licensee) agree
##    that you have read, understood, and will comply with the
##    following terms and conditions.
##    
##    Permission to copy, modify, and distribute this work, with or
##    without modification, for any purpose and without fee or royalty
##    is hereby granted, provided that you include the following on
##    ALL copies of the work or portions thereof, including
##    modifications:
##    
##     - The full text of this NOTICE in a location viewable to users
##       of the redistributed or derivative work.
##     - Any pre-existing intellectual property disclaimers, notices,
##       or terms and conditions. If none exist, the W3C Software and
##       Document Short Notice should be included.
##     - Notice of any changes or modifications, through a copyright
##       statement on the new code or document such as "This software
##       or document includes material copied from or derived from
##       [title and URI of the W3C document]. Copyright © [YEAR] W3C®
##       (MIT, ERCIM, Keio, Beihang)." 
##    
##    Disclaimers
##    -----------
##    
##    THIS WORK IS PROVIDED "AS IS," AND COPYRIGHT HOLDERS MAKE NO
##    REPRESENTATIONS OR WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT
##    NOT LIMITED TO, WARRANTIES OF MERCHANTABILITY OR FITNESS FOR ANY
##    PARTICULAR PURPOSE OR THAT THE USE OF THE SOFTWARE OR DOCUMENT
##    WILL NOT INFRINGE ANY THIRD PARTY PATENTS, COPYRIGHTS,
##    TRADEMARKS OR OTHER RIGHTS.
##    
##    COPYRIGHT HOLDERS WILL NOT BE LIABLE FOR ANY DIRECT, INDIRECT,
##    SPECIAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF ANY USE OF THE
##    SOFTWARE OR DOCUMENT.
##    
##    The name and trademarks of copyright holders may NOT be used in
##    advertising or publicity pertaining to the work without
##    specific, written prior permission. Title to copyright in this
##    work will at all times remain with copyright holders.

from .core import ASType
from .core import ASVocab, Environment, shortids_from_vocab

def as_uri(identifier):
    return "http://www.w3.org/ns/activitystreams#" + identifier


# Core classes
# ============

Object = ASType(
    as_uri("Object"), [], "Object",
    notes=(
        "Describes an object of any kind. "
        "The Object class serves as the base class for most of the "
        "other kinds of objects defined in the Activity Vocabulary, "
        "include other Core classes such as Activity, "
        "IntransitiveActivity, Actor, Collection and OrderedCollection."))

Link = ASType(
    as_uri("Link"), [], "Link",
    notes=(
        "A Link is an indirect, qualified reference to a resource identified by"
        "a URL. The fundamental model for links is established by [RFC5988]. "
        "Many of the properties defined by the Activity Vocabulary allow "
        "values that are either instances of Object or Link. When a Link is "
        "used, it establishes a qualified relation connecting the subject "
        "(the containing object) to the resource identified by the href."))

Activity = ASType(
    as_uri("Activity"), [Object], "Activity",
    notes=(
        "An Activity is a subclass of Object that describes some form of "
        "action that may happen, is currently happening, or has already "
        "happened. The Activity class itself serves as an abstract base "
        "class for all types of activities. It is important to note that "
        "the Activity class itself does not carry any specific semantics "
        "about the kind of action being taken."))

IntransitiveActivity = ASType(
    as_uri("IntransitiveActivity"), [Activity], "IntransitiveActivity",
    notes=(
        "Instances of IntransitiveActivity are a subclass of Activity whose "
        "actor property identifies the direct object of the action as opposed "
        "to using the object property."))

Actor = ASType(
    as_uri("Actor"), [Object], "Actor",
    notes=(
        "An Actor is any entity that is capable of being the primary actor "
        "for an Activity."))

Collection = ASType(
    as_uri("Collection"), [Object], "Collection",
    notes=(
        "A Collection is a subclass of Object that represents ordered or "
        "unordered sets of Object or Link instances.\n\n"
        "Refer to the Activity Streams 2.0 Core specification for a complete"
        "description of the Collection type."))

OrderedCollection = ASType(
    as_uri("OrderedCollection"), [Collection], "OrderedCollection",
    notes=(
        "A subclass of Collection in which members of the logical collection "
        "are assumed to always be strictly ordered."))

CollectionPage = ASType(
    as_uri("CollectionPage"), [Collection], "CollectionPage",
    notes=(
        "Used to represent distinct subsets of items from a Collection. "
        "Refer to the Activity Streams 2.0 Core for a complete description of "
        "the CollectionPage object."))

OrderedCollectionPage = ASType(
    as_uri("OrderedCollectionPage"), [OrderedCollection, CollectionPage],
    "OrderedCollectionPage",
    notes=(
        "Used to represent ordered subsets of items from an OrderedCollection. "
        "Refer to the Activity Streams 2.0 Core for a complete description of "
        "the OrderedCollectionPage object."))



# Extended Classes: Activity Types
# ================================

Accept = ASType(
    as_uri("Accept"), [Activity],
    "Accept",
    notes=(
        "Indicates that the actor accepts the object. "
        "The target property can be used in certain circumstances to indicate "
        "the context into which the object has been accepted. For instance, "
        "when expressing the activity, \"Sally accepted Joe into the Club\", "
        "the \"target\" would identify the \"Club\"."))

TentativeAccept = ASType(
    as_uri("TentativeAccept"), [Accept],
    "TentativeAccept",
    notes=(
        "A specialization of Accept indicating that the acceptance is "
        "tentative."))

Add = ASType(
    as_uri("Add"), [Activity],
    "Add",
    notes=(
        "Indicates that the actor has added the object to the target. If the "
        "target property is not explicitly specified, the target would need "
        "to be determined implicitly by context. The origin can be used to "
        "identify the context from which the object originated."))

Arrive = ASType(
    as_uri("Arrive"), [IntransitiveActivity],
    "Arrive",
    notes=(
        "An IntransitiveActivity that indicates that the actor has arrived "
        "at the location. The origin can be used to identify the context "
        "from which the actor originated. The target typically has no defined "
        "meaning."))

Create = ASType(
    as_uri("Create"), [Activity],
    "Create",
    notes=(
        "Indicates that the actor has created the object."))

Delete = ASType(
    as_uri("Delete"), [Activity],
    "Delete",
    notes=(
        "Indicates that the actor has deleted the object. If specified, "
        "the origin indicates the context from which the object was "
        "deleted."))

Follow = ASType(
    as_uri("Follow"), [Activity],
    "Follow",
    notes=(
        "Indicates that the actor is \"following\" the object. Following is "
        "defined in the sense typically used within Social systems in which "
        "the actor is interested in any activity performed by or on the "
        "object. The target and origin typically have no defined meaning."))

Ignore = ASType(
    as_uri("Ignore"), [Activity],
    "Ignore",
    notes=(
        "Indicates that the actor is ignoring the object. "
        "The target and origin typically have no defined meaning."))

Join = ASType(
    as_uri("Join"), [Activity],
    "Join",
    notes=(
        "Indicates that the actor has joined the object. The target and "
        "origin typically have no defined meaning."))

Leave = ASType(
    as_uri("Leave"), [Activity],
    "Leave",
    notes=(
        "Indicates that the actor has left the object. The target and origin "
        "typically have no meaning."))

Like = ASType(
    as_uri("Like"), [Activity],
    "Like",
    notes=(
        "Indicates that the actor likes, recommends or endorses the object. "
        "The target and origin typically have no defined meaning."))

Offer = ASType(
    as_uri("Offer"), [Activity],
    "Offer",
    notes=(
        "Indicates that the actor is offering the object. If specified, the "
        "target indicates the entity to which the object is being offered."))

Invite = ASType(
    as_uri("Invite"), [Offer],
    "Invite",
    notes=(
        "A specialization of Offer in which the actor is extending an "
        "invitation for the object to the target."))

Reject = ASType(
    as_uri("Reject"), [Activity],
    "Reject",
    notes=(
        "Indicates that the actor is rejecting the object. The target and "
        "origin typically have no defined meaning."))

TentativeReject = ASType(
    as_uri("TentativeReject"), [Reject],
    "TentativeReject",
    notes=(
        "A specialization of Reject in which the rejection is considered "
        "tentative."))

Remove = ASType(
    as_uri("Remove"), [Activity],
    "Remove",
    notes=(
        "Indicates that the actor is removing the object. If specified, the "
        "origin indicates the context from which the object is being removed."))

Undo = ASType(
    as_uri("Undo"), [Activity],
    "Undo",
    notes=(
        "Indicates that the actor is undoing the object. In most cases, "
        "the object will be an Activity describing some previously performed "
        "action (for instance, a person may have previously \"liked\" "
        "an article but, for whatever reason, might choose to undo that "
        "like at some later point in time).\n\n"
        "The target and origin typically have no defined meaning."))

Update = ASType(
    as_uri("Update"), [Activity],
    "Update",
    notes=(
        "Indicates that the actor has updated the object. Note, however, that "
        "this vocabulary does not define a mechanism for describing the "
        "actual set of modifications made to object.\n\n"
        "The target and origin typically have no defined meaning."))

Experience = ASType(
    as_uri("Experience"), [Activity],
    "Experience",
    notes=(
        "Indicates that the actor has experienced the object. The type of "
        "experience is not specified."))

View = ASType(
    as_uri("View"), [Experience],
    "View",
    notes=(
        "Indicates that the actor has viewed the object. Viewing is a "
        "specialization of Experience."))

Listen = ASType(
    as_uri("Listen"), [Experience],
    "Listen",
    notes=(
        "Indicates that the actor has listened to the object. Listening is a "
        "specialization of Experience."))

Read = ASType(
    as_uri("Read"), [Experience],
    "Read",
    notes=(
        "Indicates that the actor has read the object. Reading is a "
        "specialization of Experience."))

Move = ASType(
    as_uri("Move"), [Activity],
    "Move",
    notes=(
        "Indicates that the actor has moved object from origin to target. If "
        "the origin or target are not specified, either can be determined by "
        "context."))

Travel = ASType(
    as_uri("Travel"), [IntransitiveActivity],
    "Travel",
    notes=(
        "Indicates that the actor is traveling to target from origin. "
        "Travel is an IntransitiveObject whose actor specifies the direct "
        "object. If the target or origin are not specified, either can be "
        "determined by context."))

Announce = ASType(
    as_uri("Announce"), [Activity],
    "Announce",
    notes=(
        "Indicates that the actor is calling the target's attention the object."
        "\n\n"
        "The origin typically has no defined meaning."))

Block = ASType(
    as_uri("Block"), [Ignore],
    "Block",
    notes=(
        "Indicates that the actor is blocking the object. Blocking is a "
        "stronger form of Ignore. The typical use is to support social systems "
        "that allow one user to block activities or content of other users. "
        "The target and origin typically have no defined meaning."))

Flag = ASType(
    as_uri("Flag"), [Activity],
    "Flag",
    notes=(
        "Indicates that the actor is \"flagging\" the object. Flagging is "
        "defined in the sense common to many social platforms as reporting "
        "content as being inappropriate for any number of reasons."))

Dislike = ASType(
    as_uri("Dislike"), [Activity],
    "Dislike",
    notes=(
        "Indicates that the actor dislikes the object."))



# Extended Classes: Actor types
# =============================

Application = ASType(
    as_uri("Application"), [Actor],
    "Application",
    notes=(
        "Describes a software application."))

Group = ASType(
    as_uri("Group"), [Actor],
    "Group",
    notes=(
        "Represents a formal or informal collective of Actors."))

Organization = ASType(
    as_uri("Organization"), [Actor],
    "Organization",
    notes=(
        "Represents an organization."))

Person = ASType(
    as_uri("Person"), [Actor],
    "Person",
    notes=(
        "Represents an individual person."))

Process = ASType(
    as_uri("Process"), [Actor],
    "Process",
    notes=(
        "Represents a series of actions taken to achieve a particular goal."))

Service = ASType(
    as_uri("Service"), [Actor],
    "Service",
    notes=(
        "Represents a service of any kind."))



# Extended Classes: Object Types
# ==============================

Relationship = ASType(
    as_uri("Relationship"), [Object],
    "Relationship",
    notes=(
        "Describes a relationship between two individuals. "
        "The subject and object properties are used to identify the "
        "connected individuals.\n\n"
        "See 3.3.1 [of ActivityStreams 2.0 Vocabulary document] Representing "
        "Relationships Between Entities for additional information."))

Content = ASType(
    as_uri("Content"), [Object],
    "Content",
    notes=(
        "Describes an entity representing any form of content. Examples "
        "include documents, images, etc. Content objects typically are not "
        "able to perform activities on their own, yet rather are usually the "
        "object or target of activities."))

Article = ASType(
    as_uri("Article"), [Content],
    "Article",
    notes=(
        "Represents any kind of multi-paragraph written work."))

Album = ASType(
    as_uri("Album"), [Collection],
    "Album",
    notes=(
        "A type of Collection typically used to organize Image, Video or Audio "
        "objects."))

Folder = ASType(
    as_uri("Folder"), [Collection],
    "Folder",
    notes=(
        "A type of Collection typically used to organize objects such as"
        "Documents."))

Story = ASType(
    as_uri("Story"), [OrderedCollection],
    "Story",
    notes=(
        "A type of Ordered Collection usually containing Content Items "
        "organized to \"tell a story\". "))

Document = ASType(
    as_uri("Document"), [Content],
    "Document",
    notes=(
        "Represents a document of any kind."))

Audio = ASType(
    as_uri("Audio"), [Document],
    "Audio",
    notes=(
        "Represents an audio document of any kind."))

Image = ASType(
    as_uri("Image"), [Document],
    "Image",
    notes=(
        "An image document of any kind"))

Video = ASType(
    as_uri("Video"), [Content],
    "Video",
    notes=("Represents a video document of any kind."))

Note = ASType(
    as_uri("Note"), [Content],
    "Note",
    notes=(
        "Represents a short work typically less than a single "
        "paragraph in length."))

Page = ASType(
    as_uri("Page"), [Document],
    "Page",
    notes=(
        "Represents a Web Page."))

Question = ASType(
    as_uri("Question"), [Content, IntransitiveActivity],
    "Question",
    notes=(
        "Represents a question being asked. Question objects are unique in "
        "that they are an extension of both Content and IntransitiveActivity. "
        "That is, the Question object is an Activity but the direct object is "
        "the question itself."))

Event = ASType(
    as_uri("Event"), [Object],
    "Event",
    notes=(
        "Represents any kind of event."))

Place = ASType(
    as_uri("Place"), [Object],
    "Place",
    notes=(
        "Represents a logical or physical location. "
        "See 3.3.2 Representing Places [of ActivityStreams 2.0 Vocabulary "
        "document] for additional information."))

Mention = ASType(
    as_uri("Mention"), [Link],
    "Mention",
    notes=(
        "A specialized Link that represents an @mention."))

Profile = ASType(
    as_uri("Profile"), [Content],
    "Profile",
    notes=(
        "A Profile is a content object that describes another Object, "
        "typically used to describe Actor, objects. The describes property "
        "is used to reference the object being described by the profile."))




# Core definition Vocab and basic environment
# ===========================================

CoreVocab = ASVocab(
    [Object, Link, Activity, IntransitiveActivity, Actor, Collection,
     OrderedCollection, CollectionPage, OrderedCollectionPage,
     Accept, TentativeAccept, Add, Arrive, Create, Delete,
     Follow, Ignore, Join, Leave, Like, Offer, Invite, Reject,
     TentativeReject, Remove, Undo, Update, Experience, View,
     Listen, Read, Move, Travel, Announce, Block, Flag, Dislike,
     Application, Group, Organization, Person, Process, Service,
     Relationship, Content, Article, Album, Folder, Story, Document,
     Audio, Image, Video, Note, Page, Question, Event, Place, Mention,
     Profile])

BasicEnv = Environment(
    # @@: Maybe this one should be implied?
    vocabs=[CoreVocab],
    shortids=shortids_from_vocab(CoreVocab),
    c_accessors=shortids_from_vocab(CoreVocab))
# alias
Env = BasicEnv
