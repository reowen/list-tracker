import webapp2
import jinja2
import admin
import logging

from google.appengine.api import mail
from google.appengine.ext import deferred

"""
User registration and login classes
"""

class Signup(admin.Handler):
    def get(self):
        if self.user:
            self.redirect('/')
        else:
            self.render('signup.html')

    def post(self):
        has_error = False
        firstname = self.request.get('firstname')
        lastname = self.request.get('lastname')
        email = self.request.get('email')
        #email should not be case-sensitive
        email = email.lower()
        password = self.request.get('password')
        verify = self.request.get('verify')
        group = self.request.get('group')

        #pull variables in case of group-invite
        g = self.request.get('g')
        v = self.request.get('v')
        group_invite = self.request.get('group-invite')

        params = dict(firstname = firstname, lastname = lastname,
                      email = email)

        if not firstname:
            params['firstname_error'] = "First name is required"
            has_error = True
        if not lastname:
            params['lastname_error'] = "Last name is required"
            has_error = True

        if not valid_email(email):
            params['email_error'] = "That's not a valid email."
            has_error = True
        elif not email:
            params['email_error'] = "Please enter an email."
        else:
            if admin.User.by_email(email):
                params['email_error'] = "Another account is using this email."
                has_error = True

        if not valid_password(password):
            params['pw_error'] = "That wasn't a valid password."
            has_error = True
        elif password != verify:
            params['verify_error'] = "Your passwords didn't match."
            has_error = True

        if has_error:
            self.render('signup.html', **params)
        else:
            u = admin.User.register(firstname, lastname, email, password)
            u.put()
            self.login(u)
            if group_invite:
                self.redirect('/my-groups/join-group-email?g=%s&v=%s&u=%s&group-invite=%s' % (g, v, u.key.id(), group_invite))
            else:
                self.redirect('/signup/welcome')

#consider updating the validations for this class
class Login(admin.Handler):
    def get(self):
        if self.user:
            self.redirect('/')
        else:
            #in case of a group-invite
            g = self.request.get('g')
            v = self.request.get('v')
            group_invite = self.request.get('group-invite')
            params = dict(g = g, v = v, group_invite = group_invite)
            self.render('login.html', **params)
    def post(self):
        email = self.request.get('email')
        #email should not be case-sensitive
        email = email.lower()
        password = self.request.get('password')
        remember = self.request.get('remember')
        #pull variables to see if they've been invited to join a group
        g = self.request.get('g')
        v = self.request.get('v')
        group_invite = self.request.get('group-invite')
        params = dict(email = email, g = g, v = v, group_invite = group_invite)

        u = admin.User.login(email, password)
        if u:
            #if they clicked "keep me logged in"
            if remember:
                self.remember_login(u)
            else:
                self.login(u)
            if group_invite:
                self.redirect('/my-groups/join-group-email?g=%s&v=%s&u=%s&group-invite=%s' % (g, v, u.key.id(), group_invite))
            else:
                self.redirect('/')
        else:
            email_found = admin.User.by_email(email)
            if not email_found:
                params['email_error'] = "Email not found."
            else:
                #this error msg would also come up if email not in system
                params['pw_error'] = 'Email and password do not match.'
            self.render('login.html', **params)

class Logout(admin.Handler):
    def get(self):
        self.logout()
        self.redirect('/')


"""
Account Management Classes
"""

class ChangePassword(admin.Handler):
    def get(self):
        if not self.user:
            self.redirect('/')
        else:
            self.render('change-password.html', user = self.user)

    def post(self):
        current_pw = self.request.get('current_password')
        new_password = self.request.get('new_password')
        verify = self.request.get('verify')

        has_error = False
        params = dict(user = self.user)

        u = admin.User.login(self.user.email, current_pw)
        if not u:
            params['pw_error'] = 'Password incorrect.'
            has_error = True
        elif new_password != verify:
            params['new_pw_error'] = 'New password and verify password do not match.'
            has_error = True

        if has_error:
            self.render('change-password.html', **params)

        else:
            new_pw_hash = admin.make_pw_hash(self.user.email, new_password)
            u.pw = new_pw_hash
            u.put()
            params['pw_success'] = 'Successfully changed your password.'
            self.render('change-password.html', **params)


class ChangeEmail(admin.Handler):
    def get(self):
        if self.user:
            self.render('change-email.html', user = self.user)
        else:
            self.redirect('/')

    def post(self):
        has_error = False
        email = self.request.get('email')
        #email should not be case-sensitive
        email = email.lower()
        new_email = self.request.get('new_email')
        new_email = new_email.lower()
        verify_email = self.request.get('verify_email')
        verify_email = verify_email.lower()
        email_password = self.request.get('email_password')

        params = dict(user = self.user, email=email)

        u = admin.User.login(email, email_password)
        if not u:
            params['email_error'] = 'Email and password do not match'
            self.render('change-email.html', **params)

        if not valid_email(new_email):
            params['new_email_error'] = "That's not a valid email."
            has_error = True
        elif new_email != verify_email:
            params['verify_email_error'] = "New email field doesn't match the verify email field."
            has_error = True

        if has_error:
            self.render('change-email.html', **params)
        else:
            key = admin.User.by_id(self.user.key.id())
            if key:
                key.email = new_email
                #you have to hash the password with the new user email,
                #otherwise the login function won't work.
                key.pw = admin.make_pw_hash(new_email, email_password)
                key.put()
                params['email'] = new_email
                params['email_success'] = 'Email successfully changed to %s' % new_email
                self.render('change-email.html', **params)


recoveremail = mail.EmailMessage(sender="list.tracker.app@gmail.com",
                                 subject="List-Tracker recover password")
class RecoverPassword(admin.Handler):
    def get(self):
        self.render('recover-password.html')
    def post(self):
        email = self.request.get('email')
        params = dict(email = email)
        if not email:
            self.redirect('/recover-password')
            return
        acct = admin.User.by_email(email)
        if not acct:
            params['email_error'] = 'Email not found.'
            self.render('recover-password.html', **params)
            return
        else:
            recover_key = admin.make_random_string()
            # logging.info('recover key: %s' % recover_key)
            acct.recover = admin.make_pw_hash(acct.email, recover_key)

            recoveremail.to = email
            recoveremail.body = """
            Dear %s,

            You recently requested to recover a forgotten password. Click the link below to reset your password.

            https://list-tracker.appspot.com/reset-pw?u=%s&v=%s

            -The list-tracker team.
            """ % (acct.firstname, acct.key.id(), recover_key)

            #put email into task queue
            deferred.defer(admin.send_email, recoveremail)

            #send recover password back to datastore
            acct.put()

            params['success'] = 'An email has been sent to %s.  It may take a few minutes to arrive.' % email
            self.render('recover-password.html', **params)


class ResetPassword(admin.Handler):
    def get(self):
        self.logout()
        u = self.request.get('u')
        v = self.request.get('v')
        params = {}
        acct = None
        invalid_link_msg = 'Invalid link.  Please <a href="/recover-password">click here to send a new recover password email.</a>'
        if not u:
            params['invalid'] = invalid_link_msg
        else:
            acct = admin.User.by_id(int(u))
            if not acct:
                params['invalid'] = invalid_link_msg
            else:
                if not admin.check_pw(acct.email, v, acct.recover):
                    params['invalid'] = invalid_link_msg
                else:
                    params['email'] = acct.email
        if v == 'default':
            params['invalid'] = invalid_link_msg

        self.render('reset-password.html', **params)

    def post(self):
        password = self.request.get('password')
        verify = self.request.get('verify')
        u = self.request.get('u')
        v = self.request.get('v')
        if not u:
            params['invalid'] = 'Something went wrong.  Please <a href="/recover-password">click here to send a new recover password email.</a>'
            self.render('reset-password.html', **params)
            return

        has_error = False
        params = dict()

        acct = admin.User.by_id(int(u))
        if not acct:
            params['invalid'] = 'Something went wrong.  Please <a href="/recover-password">click here to send a new recover password email.</a>'
            self.render('reset-password.html', **params)
            return
        elif not admin.check_pw(acct.email, v, acct.recover):
            params['invalid'] = 'Something went wrong.  Please <a href="/recover-password">click here to send a new recover password email.</a>'
        elif password != verify:
            params['pw_error'] = 'Password and verify password do not match.'
            has_error = True

        params['email'] = acct.email
        if has_error:
            self.render('reset-password.html', **params)

        else:
            new_pw_hash = admin.make_pw_hash(acct.email, password)
            acct.pw = new_pw_hash
            acct.recover = 'default'
            acct.put()
            params['success'] = 'Successfully changed your password.'
            self.render('reset-password.html', **params)


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
    users = list(users)
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
