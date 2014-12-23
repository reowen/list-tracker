import os
import jinja2
import webapp2
import logging
import datetime

from google.appengine.ext import ndb
from google.appengine.api import memcache
from google.appengine.api import mail
from google.appengine.ext import deferred

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)


"""
App-Global Handlers
"""
class Cookie():
    #login just sets the user cookie
    def login(self, user):
        self.set_cookie('user', str(user.key.id()))

    def remember_login(self, user):
        expires = datetime.datetime.now() + datetime.timedelta(days = 30)
        self.set_cookie('user', str(user.key.id()), expires = expires)

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user=; Path=/')
        #below, only works in webapp2. not all frameworks have it
        #self.clear_cookie('user')

    def set_cookie(self, cookie_name, val, expires = None):
        secure_val = make_secure_val(val)
        if expires:
            return self.response.set_cookie(cookie_name, secure_val,
                                            expires=expires)
        else:
            cookie_val = '%s=%s; Path=/' % (cookie_name, secure_val)
            return self.response.headers.add_header('Set-Cookie',
                                                    cookie_val.encode('ascii'))

    def clear_cookie(self, cookie_name):
        return self.response.delete_cookie(cookie_name)

    def return_secure_cookie(self, cookie_name):
        cookie_str = self.request.cookies.get(cookie_name)
        if cookie_str:
            cookie_val = check_secure_val(cookie_str)
            return cookie_val

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def get_cookie_val(self, cookie):
        return cookie.split('|')[0]

    def set_referer(self):
        referer = self.request.url
        #self.response.headers.add_header(

    def from_path(self):
        h = self.request.headers
        return h['Referer']

class Handler(webapp2.RequestHandler, Cookie):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user')
        self.user = uid and User.by_id(int(uid))
        #self.user_id = self.return_secure_cookie('user')


"""
Member Class
"""

def member_key(name = 'default'):
    return ndb.Key('Member', name)

class Member(ndb.Model):
    #User-ID
    member = ndb.IntegerProperty(required = True)
    #Member's first and last name
    membername = ndb.StringProperty(required = True)
    #Group-ID
    group = ndb.StringProperty(required = True)
    groupname = ndb.StringProperty(required = True)
    creator = ndb.BooleanProperty(required = True)
    admin = ndb.BooleanProperty(required = True)
    date_joined = ndb.DateTimeProperty(auto_now_add=True)

    @classmethod
    def by_id(cls, m_id):
        return cls.get_by_id(m_id, parent = member_key())

    @classmethod
    #user_id is the string extracted from the cookie
    def by_member(cls, user_id, ancestor_key = member_key()):
        m = cls.query(cls.member == user_id, ancestor = ancestor_key).order(-cls.date_joined).fetch(20)
        return m

    @classmethod
    def by_group_id(cls, group_id, ancestor_key = member_key()):
        g = cls.query(cls.group == group_id, ancestor = ancestor_key).fetch()
        return g

    @classmethod
    def by_groupname(cls, groupname, ancestor_key = member_key()):
        g = cls.query(cls.groupname == groupname, ancestor = ancestor_key).fetch()
        return g

    @classmethod
    def by_entity(cls, group_id, member_id, ancestor_key = member_key()):
        e = cls.query(cls.group == group_id, cls.member == member_id,
                      ancestor = ancestor_key).get()
        return e

    @classmethod
    def add(cls, group_id, member_id, groupname, creator = False, admin = False):
        groupcheck = Member.query(Member.member == member_id,
                                  Member.groupname == groupname,
                                  ancestor=member_key()).get()
        if groupcheck:
            return None
        m = User.by_id(member_id)
        if m:
            membername = m.firstname + ' ' + m.lastname
        if groupname and membername:
            return Member(parent = member_key(),
                           member = member_id,
                           membername = membername,
                           group = group_id,
                           groupname = groupname,
                           creator = creator,
                           admin = admin)
        else:
            return None

"""
Group Class
"""

#adjust group key to allow for different group types
def group_key(group_name = 'default'):
    return ndb.Key('WishlistGroup', group_name)

class Group(ndb.Model):
    groupname = ndb.StringProperty(required = True)
    pw = ndb.StringProperty(required = True)
    creator = ndb.IntegerProperty(required = True)
    admin = ndb.StringProperty()
    join_key = ndb.StringProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)

    @classmethod
    def by_name(cls, groupname, ancestor_key = group_key()):
        g = cls.query(cls.groupname == groupname, ancestor=ancestor_key).get()
        return g

    @classmethod
    def by_id(cls, gid):
        return cls.get_by_id(gid, parent = group_key())

    @classmethod
    #creator must be an integer, representing the user_id extracted from
    #the cookie
    def create(cls, groupname, pw, creator, admin = None):
        pw_hash = make_pw_hash(groupname, pw)
        return Group(parent = group_key(),
                     groupname = groupname,
                     pw = pw_hash,
                     creator = creator,
                     admin = admin)

    @classmethod
    def join(cls, groupname, pw):
        g = cls.by_name(groupname)
        if g and check_pw(groupname, pw, g.pw):
            return g

    @staticmethod
    def members_set_cache(group_id, members):
        memcache.set('group_members: %s' % group_id, members)

    @staticmethod
    def get_cached_members(group_id):
        m = memcache.get('group_members: %s' % group_id)
        if m:
            members = m
        else:
            members = None
        return members

    @staticmethod
    def get_members(group_id, update = False, ancestor_key = member_key()):
        members = Group.get_cached_members(group_id)
        if members is None or update:
            members = Member.query(Member.group == group_id, ancestor = ancestor_key).fetch()
            members = list(members)
            Group.members_set_cache(group_id, members)
            logging.info('Memcache set for group_members: %s', group_id)
        else:
            logging.info('Memcache hit for key group_members: %s', group_id)
        return members



"""
User Class
"""

def user_key(user_name = 'default'):
    return ndb.Key('Users', user_name)

class User(ndb.Model):
    firstname = ndb.StringProperty(required = True)
    lastname = ndb.StringProperty(required = True)
    pw = ndb.StringProperty(required = True)
    recover = ndb.StringProperty()
    email = ndb.StringProperty(required = True)

    @classmethod
    def by_id(cls, uid):
        return cls.get_by_id(uid, parent = user_key())

    @classmethod
    def by_email(cls, email, ancestor_key = user_key()):
        u = cls.query(cls.email == email, ancestor=ancestor_key).get()
        return u

    @classmethod
    def register(cls, firstname, lastname, email, pw, groups = None,
                 recover = 'default'):
        pw_hash = make_pw_hash(email, pw)
        return User(parent = user_key(),
                    firstname = firstname,
                    lastname = lastname,
                    email = email,
                    pw = pw_hash,
                    recover = recover)

    @classmethod
    def login(cls, email, pw):
        u = cls.by_email(email)
        if u and check_pw(email, pw, u.pw):
            return u

    @staticmethod
    def groups_set_cache(user_id, groups):
        memcache.set('user_groups: %s' % user_id, groups)

    @staticmethod
    def get_cached_groups(user_id):
        g = memcache.get('user_groups: %s' % user_id)
        if g:
            groups = g
        else:
            groups = None
        return groups

    @staticmethod
    def get_groups(user_id, update = False, ancestor_key = member_key()):
        groups = User.get_cached_groups(user_id)
        if groups is None or update:
            groups = Member.query(Member.member == user_id,
                                  ancestor=ancestor_key).order(-Member.date_joined).fetch()
            groups = list(groups)
            User.groups_set_cache(user_id, groups)
            logging.info('Memcache set for user_groups: %s', user_id)
        else:
            logging.info('Memcache hit for user_groups: %s', user_id)
        return groups


"""
List Classes
"""

def wishlist_key(user_name = 'default'):
    return ndb.Key('Wishlist', user_name)

class WishList(ndb.Model):
    listname = ndb.StringProperty(required = True)
    creator_id = ndb.IntegerProperty(required = True)
    firstname = ndb.StringProperty(required = True)
    group = ndb.StringProperty(required = True)
    groupname = ndb.StringProperty(required = True)
    for_other_person = ndb.BooleanProperty(required = True)
    created = ndb.DateTimeProperty(auto_now_add=True)
    items = ndb.JsonProperty(required = True)
##    #items format below (list of dictionaries
##    items = [{'item': name, 'link': url, 'note': note,
##              'bought': [buyer_id, buyer_name]}, {'item': item, ...} ]


    @classmethod
    def by_id(cls, list_id):
        return cls.get_by_id(list_id, parent = wishlist_key())

    @classmethod
    def by_name(cls, listname, group_id, ancestor_key = wishlist_key()):
        l = cls.query(cls.listname == listname,
                      cls.group == group_id,
                      ancestor=ancestor_key).get()
        return l

    @classmethod
    def by_user_group(cls, user_id, group_id, ancestor_key = wishlist_key()):
        lists = cls.query(cls.creator_id == user_id,
                          cls.group == group_id,
                          ancestor=ancestor_key).fetch()
        return lists

    @classmethod
    def save(cls, listname, user_id, firstname, group,
             groupname, items, for_other_person = False):
        return WishList(parent = wishlist_key(),
                        listname = listname,
                        creator_id = user_id,
                        firstname = firstname,
                        group = group,
                        groupname = groupname,
                        items = items,
                        for_other_person = for_other_person)

    @classmethod
    def update_items(cls, list_id, items):
        l = cls.by_id(list_id)
        l.items = items
        return l

    @staticmethod
    def remove_group(l):
        l.group = '---groupless---'
        l.groupname = '---groupless---'
        return l

    @staticmethod
    def set_user_lists_cache(user_id, lists):
        memcache.set('user_lists: %s' % user_id, lists)

    @staticmethod
    def get_cached_user_lists(user_id):
        l = memcache.get('user_lists: %s' % user_id)
        if l:
            lists = l
        else:
            lists = None
        return lists

    @classmethod
    def by_user(cls, user_id, update = False, ancestor_key = wishlist_key()):
        lists = cls.get_cached_user_lists(user_id)
        if lists is None or update:
            lists = cls.query(cls.creator_id == user_id,
                              ancestor=ancestor_key).order(-cls.created).fetch()
            lists = list(lists)
            cls.set_user_lists_cache(user_id, lists)
            logging.info('Memcache set for user_lists: %s', user_id)
        else:
            logging.info('Memcache hit for user_lists: %s', user_id)
        return lists

    @staticmethod
    def set_group_lists_cache(group_id, lists):
        memcache.set('group_lists: %s' % group_id, lists)

    @staticmethod
    def get_cached_group_lists(group_id):
        l = memcache.get('group_lists: %s' % group_id)
        if l:
            lists = l
        else:
            lists = None
        return lists

    @classmethod
    def by_group(cls, group_id, update = False, ancestor_key = wishlist_key()):
        lists = cls.get_cached_group_lists(group_id)
        if lists is None or update:
            lists = cls.query(cls.group == group_id,
                              ancestor=ancestor_key).order(-WishList.created).fetch()
            lists = list(lists)
            cls.set_group_lists_cache(group_id, lists)
            logging.info('Memcache set for group_lists: %s', group_id)
        else:
            logging.info('Memcache hit for group_lists: %s', group_id)
        return lists



import hmac
import hashlib
import random
import string

"""
Cookie security procedures
"""
try:
    import limelight
    secret = limelight.Secret.secret
except ImportError:
    secret = 'limelight'

def hash_str(s):
    return hmac.new(secret, s).hexdigest()

def make_secure_val(s):
    return '%(string)s|%(hash)s' % {'string': s, 'hash': hash_str(s)}

def check_secure_val(h):
    val = h.split('|')[0]
    if h == make_secure_val(val):
        return val

"""
Password security procedures
"""
def make_random_string(size=30, chars=string.ascii_uppercase + string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for __ in range(size))

def make_salt(size=5, chars=string.ascii_uppercase + string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for __ in range(size))

#first, set a default value for salt as none
def make_pw_hash(name, pw, salt = None):
    #only want to generate salts when we make a new password hash
    #so we check if a salt exists, then make a salt if it doesn't
    #if a salt already exists, we'll use the existing
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (h, salt)

def check_pw(name, pw, h):
    #we set the salt value to whatever's after the comma in h
    salt = h.split(',')[1]
    #then we pass the extracted salt through our make_pw_hash function
    return h == make_pw_hash(name, pw, salt)

"""
Email procedures
"""

def send_email(message):
    logging.info('Sending email to %s' % message.to)
    message.send()
