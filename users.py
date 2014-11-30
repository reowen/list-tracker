import webapp2
import jinja2
import admin

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
            self.redirect('/signup/welcome')
##            if group == 'join':
##                self.redirect('/my-groups/join-group')
##            if group == 'create':
##                self.redirect('/my-groups/create-group')
##            else:
##                self.redirect('/')

#consider updating the validations for this class           
class Login(admin.Handler):
    def get(self):
        if self.user:
            self.redirect('/')
        else:
            self.render('login.html')

    def post(self):
        email = self.request.get('email')
        #email should not be case-sensitive
        email = email.lower()
        password = self.request.get('password')
        remember = self.request.get('remember')
        params = dict(email = email)

        u = admin.User.login(email, password)
        if u:
            if remember:
                self.remember_login(u)
            else:
                self.login(u)
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

class ResetPassword(admin.Handler):
    def get(self):
        self.render('reset-password.html')

    def post(self):
        email = self.request.get('email')
        #email should not be case-sensitive
        email = email.lower()
        new_password = self.request.get('new_password')
        verify = self.request.get('verify')

        has_error = False
        params = dict()

        account = admin.User.by_email(email)
        if not account:
            params['email_error'] = 'There is no account with this email.'
            has_error = True
        elif new_password != verify:
            params['new_pw_error'] = 'New password and verify password do not match.'
            has_error = True
            
        if has_error:
            self.render('reset-password.html', **params)

        else:
            new_pw_hash = admin.make_pw_hash(email, new_password)
            account.pw = new_pw_hash
            account.put()
            params['pw_success'] = 'Successfully changed your password.'
            self.render('reset-password.html', **params)

            
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
                params['email_success'] = 'Email successfully changed to %s' % new_email
                self.render('change-email.html', **params)

    

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



