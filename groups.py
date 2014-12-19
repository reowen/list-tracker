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
            #add as a group member
            group_id = str(g_key.id())
            member_id = self.user.key.id()
            creator = True
            member = admin.Member.add(group_id, member_id,
                                      groupname, creator)
            if member:
                member.put()
                time.sleep(0.1)
                #update group-members cache
                admin.Group.get_members(str(g_key.id()), update = True)
                #update user-groups cache
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

class FindGroup(admin.Handler):
    def get(self):
        if self.user:
            self.render('front.html', user = self.user,
                        text='Find Group feature is under development')
        else:
            self.redirect('/')

class InviteToGroup(admin.Handler):
    def get(self):
        if self.user:
            self.render('front.html', user = self.user,
                        text='Invite to group feature is under development')
        else:
            self.redirect('/')

class DeleteGroup(admin.Handler):
    def get(self):
        if self.user:
            self.render('front.html', user = self.user,
                        text='Delete Group feature is under development')
        else:
            self.redirect('/')

class LeaveGroup(admin.Handler):
    referer = '/'
    def get(self):
        if not self.user:
            self.redirect('/')
        else:
            LeaveGroup.referer = self.request.headers.get('referer', '/')
            params = dict(user = self.user,
                          referer = LeaveGroup.referer)
            group_id = int(self.request.get('g'))
            if not group_id:
                self.redirect('/')
                return
            group = admin.Group.by_id(group_id)
            if not group:
                params['error'] = 'There was an error processing your request. Return to the home page and try again.'
                self.render('leave-group.html', **params)
                return
            params['group'] = group
            self.render('leave-group.html', **params)

    def post(self):
        delete = self.request.get('delete')
        group_id = int(self.request.get('g'))
        params = dict(user = self.user,
                      referer = LeaveGroup.referer)

        if not group_id:
            params['error'] = 'There was an error processing your request. Return to the home page and try again.'
            self.render('leave-group.html', **params)
            return

        group = admin.Group.by_id(group_id)
        if not group:
            params['error'] = 'There was an error processing your request. Return to the home page and try again.'
            self.render('leave-group.html', **params)
            return

        elif delete:
            params['group'] = group
            #delete from member list
            member = admin.Member.by_entity(str(group_id), self.user.key.id())
            if member:
                member.key.delete()
            else:
                params['error'] = 'Could not find your group membership.'
                self.render('leave-group.html', **params)
                return
            #delete user's lists for the group
            grouplists = admin.WishList.by_user_group(self.user.key.id(), str(group_id))
            if grouplists:
                grouplists.key.delete()

            time.sleep(0.1)
            #update group-members cache
            admin.Group.get_members(str(group_id), update = True)
            #update user-lists cache
            lists = admin.WishList.by_user(self.user.key.id(), update = True)
            #update group-lists cache
            admin.WishList.by_group(str(group_id), update = True)
            #update user-groups cache
            admin.User.get_groups(self.user.key.id(), update = True)

            params['success'] = 'Successfully left %s' % group.groupname
            self.render('leave-group.html', **params)
            return
        elif not delete:
            refresh = self.request.path + '?g=%s' % group_id
            self.redirect(refresh)

class RemoveMember(admin.Handler):
    referer = '/'
    groupname = ''
    editor = False
    def get(self):
        if not self.user:
            self.redirect('/')
        else:
            group_id = self.request.get('g')
            RemoveMember.referer = self.request.headers.get('referer', '/')
            #must redirect if group doesn't exist
            group = admin.Group.by_id(int(group_id))
            if not group:
                self.redirect('/')
                return

            #only admins and creators can view this page
            m = admin.Member.by_entity(group_id, self.user.key.id())
            if not m:
                self.redirect('/')
                return
            elif m.creator:
                RemoveMember.editor = True
            elif m.admin:
                RemoveMember.editor = True

            if not RemoveMember.editor:
                self.redirect('/')
                return
            RemoveMember.groupname = group.groupname
            members = list(admin.Group.get_members(group_id))
            #if you are the only member in the group
            if len(members) == 1 and members[0].member == self.user.key.id():
                members = None

            self.render('remove-member.html', user = self.user,
                        groupname = RemoveMember.groupname,
                        members = members,
                        referer = RemoveMember.referer,
                        group_id = group_id)
    def post(self):
        group_id = self.request.get('g')
        if not group_id:
            self.redirect('/')
            return
        members = list(admin.Group.get_members(group_id))
        if not members:
            self.redirect('/manage-groups')
            return
        groupname = str(members[0].groupname)
        #list of people removed
        removed = []
        for member in members:
            remove_request = 'remove_%s' % member.member
            remove = self.request.get(remove_request)
            remove_me = 'poop'
            if remove:
                removed.append(member.membername)
                #store user-id, so user-groups cache can be updated
                m_id = int(member.member)
                #remove member entry from datastore
                member.key.delete()
                time.sleep(0.1)
                #update user-groups cache
                admin.User.get_groups(m_id, update = True)
                #remove group references from member's lists
                lists = list(admin.WishList.by_user_group(m_id, group_id))
                if lists:
                    for l in lists:
                        l.group = '---groupless---'
                        l.groupname = '---groupless---'
                        l.put()
                    #update user-lists cache
                    lists = admin.WishList.by_user(m_id, update = True)

        time.sleep(0.1)
        #update group-members cache
        admin.Group.get_members(str(group_id), update = True)
        #update group-lists cache
        admin.WishList.by_group(str(group_id), update = True)

        if removed:
            success = 'Removed the following members:'
        else:
            success = 'No members removed'
            removed = None

        self.render('remove-member.html', user = self.user,
                    groupname = groupname,
                    success = success,
                    removed = removed,
                    group_id = group_id)



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
