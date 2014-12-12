import webapp2
import jinja2
import admin
import time

import json

"""
Managing Groups
"""
           
class CreateGroup(admin.Handler):
    def get(self):
        if self.user:
            self.render('create-group.html', user = self.user)
        else:
            self.redirect('/')
    def post(self):
        has_error = False
        groupname = self.request.get('groupname')
        verify_groupname = self.request.get('verify_groupname')
        password = self.request.get('password')
        verify = self.request.get('verify')
        invite = self.request.get('invite')

        params = dict(user = self.user, groupname = groupname,
                      verify_groupname = verify_groupname)

        if not groupname:
            params['groupname_error'] = "Group name is required."
            has_error = True
        elif groupname != verify_groupname:
            params['verify_groupname_error'] = "Group names do not match."
            has_error = True
        elif admin.Group.by_name(groupname):
            params['groupname_error'] = "Group name already exists."
            has_error = True

        if not valid_password(password):
            params['pw_error'] = "That wasn't a valid password."
            has_error = True
        elif password != verify:
            params['verify_error'] = "Your passwords didn't match."
            has_error = True

        if has_error:
            self.render('create-group.html', **params)
        else:
            creator = self.user.key.id()
            g = admin.Group.create(groupname, password, creator)
            g_key = g.put()
            member = admin.Member.add(str(g_key.id()), creator,
                                      groupname)
            if member:
                member.put()
                time.sleep(0.1)
                admin.Group.get_members(str(g_key.id()), update = True)
                admin.User.get_groups(self.user.key.id(), update = True)
                self.redirect('/groups?g=%s' % g_key.id())
##                self.render('create-group.html', user = self.user,
##                            success = 'Successfully created group %s' % groupname)
            else:
                params['groupname_error'] = 'There was an error processing your request.'
                self.render('create-group.html', **params)
                            


##            if invite == 'now':
##                self.redirect('/invite-to-group')
##            else:
##                self.redirect('/')

           
class JoinGroup(admin.Handler):
    def get(self):
        if self.user:
            self.render('join.html', user = self.user)
        else:
            self.redirect('/')
    def post(self):
        has_error = False
        groupname = self.request.get('groupname')
        password = self.request.get('password')

        g = admin.Group.join(groupname, password)
        if not g:
            self.render('join.html', user = self.user,
                        error = 'Group name and password do not match.')
        else:
            member = admin.Member.add(str(g.key.id()), self.user.key.id(),
                                      groupname)
            if member:
                member.put()
                time.sleep(0.1)
                admin.Group.get_members(str(g.key.id()), update = True)
                admin.User.get_groups(self.user.key.id(), update = True)
                self.redirect('/groups?g=%s' % g.key.id())
##                self.render('join.html', user = self.user,
##                            success = 'Successfully joined %s' % groupname)
            else:
                self.render('join.html', user = self.user,
                            error = 'You already belong to this group')
            
##            user = admin.User.by_id(int(self.user_id))
##            members = g.members
##            members[self.user_id] = [user.firstname, user.lastname]
##            g.put()
##            group = g.groupname
##            m = admin.GroupMember.add(group, self.user_id)
##            m.put()
##            self.redirect('/')

class InviteToGroup(admin.Handler):
    def get(self):
        if self.user:
            self.render('front.html', user = self.user,
                        text='Invite to group feature is under development')
        else:
            self.redirect('/')
        
class LeaveGroup(admin.Handler):
    def get(self):
        if self.user:
            self.render('front.html', user = self.user,
                        text='Leave group feature is under development')
        else:
            self.redirect('/')

class FindGroup(admin.Handler):
    def get(self):
        if self.user:
            self.render('front.html', user = self.user,
                        text='Find Group feature is under development')
        else:
            self.redirect('/')
 

"""
Form validation procedures
"""

import re
#defines valid characters, must be b/w 3-20 characters
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

def get_user_key(username):
    users = db.GqlQuery("select * from User")
    for user in users:
        if user.user == username:
            return user

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)


import hmac
import hashlib
import random
import string

"""
Cookie security procedures
"""

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



