import webapp2
import jinja2
import admin

import time
from google.appengine.ext import ndb

class MainPage(admin.Handler):
    def get(self):
        if self.user:
            groups = admin.User.get_groups(self.user.key.id())
            lists = admin.WishList.by_user(self.user.key.id())
            self.render('front.html', user = self.user,
                        groups=groups, lists=lists)
        else:
            self.redirect('/login')

class ManageAccount(admin.Handler):
    def get(self):
        if not self.user:
            self.redirect('/')
        else:
            self.render('account-management.html',
                        user = self.user)

welcome_page = """
<h2>Welcome to List Tracker</h2>
<pre>Let's get started:

You can join an existing group: <a href="/my-groups/join-group">Join a Group</a>

Or you can create a new group: <a href="/my-groups/create-group">Create a Group</a>
</pre>
"""

class Welcome(admin.Handler):
    def get(self):
        if not self.user:
            self.redirect('/')
        else:
            self.render('front.html', user = self.user,
                        text = welcome_page)


"""
Group Pages
"""

class GroupMembers(admin.Handler):
    def get(self):
        group_id = self.request.get('g')
        members = admin.Group.get_members(group_id)
        text = members
        self.render('front.html', text = text)

class MyGroups(admin.Handler):
    def get(self):
        if self.user:
            self.render('manage-my-groups.html', user = self.user,
                        text = 'Manage My Groups under development')
        else:
            self.redirect('/')

class GroupPage(admin.Handler):
    #class variables to be used in both GET and POST
    group_lists = []
    groupname = ''
    group_id = ''
    def get(self):
        if not self.user:
            self.redirect('/login')
        else:
            #we always want an empty list the first time we load the page
            GroupPage.group_lists = []
            referer = self.request.headers.get('referer', '/')
            group_id = self.request.get('g')
            g = admin.Group.by_id(int(group_id))
            if not g:
                self.redirect('/')
            else:
                params = dict(user = self.user,
                              groupname = g.groupname,
                              group_id = g.key.id())
                #extract the lists for the group
                raw_group_lists = list(admin.WishList.by_group(group_id))

            if not raw_group_lists:
                params['no_list_msg'] = '%s currently has no lists.  Click the above link to create a list.' % g.groupname
                if 'my-groups/create-group' in referer:
                    params['create_success'] = 'Successfully created group %s!  Click the link below to create a list.' % g.groupname
                elif 'my-groups/join-group' in referer:
                    params['create_success'] = 'Successfully joined group %s!  Here, you can view the lists for this group, or create your own list by clicking the link below.' % g.groupname
                self.render('group-page.html', **params)
            elif len(raw_group_lists) == 1 and raw_group_lists[0].creator_id == self.user.key.id():
                params['no_list_msg'] = '%s currently has no lists to display. Tell your friends to make a list!' % g.groupname
                self.render('group-page.html', **params)
            else:
                #groupname, id class variables to be used in POST
                GroupPage.groupname = g.groupname
                GroupPage.group_id = g.key.id()

                #create dictionary of lists to pass through jinja template
                #group_lists dict class variable to be used in POST request
                for g_list in raw_group_lists:
                    GroupPage.group_lists.append({'listname': g_list.listname,
                                                  'list_id': g_list.key.id(),
                                                  'creator_id': g_list.creator_id,
                                                  'other_person': g_list.for_other_person,
                                                  'items': g_list.items})
                params['group_lists'] = GroupPage.group_lists
                self.render('group-page.html', **params)

    def post(self):
        #update = True when something is bought (in any list).
        #if update = False, clicking submit does nothing
        update = False
        group_id = self.request.get('g')
        params = dict(user = self.user,
                      groupname = GroupPage.groupname,
                      group_id = GroupPage.group_id)

        #for each list in the group, iterate over items and update bought items
        for g_list in GroupPage.group_lists:
            raw_items = g_list['items']
            for item in raw_items:
                bought_req = 'buy_%s_%s' % (str(g_list['list_id']), item['item'])
                unbuy_req = 'un' + bought_req
                bought = self.request.get(bought_req)
                unbought = self.request.get(unbuy_req)

                if bought:
                    g_list['updated'] = True
                    item['bought'] = [self.user.key.id(), self.user.firstname]
                    item['checked'] = "CHECKED"
                    update = True
                if unbought:
                    g_list['updated'] = True
                    del item['bought']
                    update = True

        #after updating in the loop above, pass new lists through template
        params['group_lists'] = GroupPage.group_lists

        #if someone bought anything, find the modified lists and save them
        if update:
            for save_list in GroupPage.group_lists:
                if 'updated' in save_list:
                    export_items = format_bought_items(save_list['items'])
                    if export_items:
                        save = admin.WishList.update_items(save_list['list_id'],
                                                           export_items)
                        if save:
                            save.put()
                            time.sleep(0.1)
                            #update user-lists cache
                            admin.WishList.by_user(self.user.key.id(), update = True)
                        else:
                            params['text'] = 'There was an error.'
            #update group-lists cache
            admin.WishList.by_group(group_id, update = True)

        self.render('group-page.html', **params)





"""
Functions for extracting, formatting item lists
"""

def format_bought_items(bought_items):
    return_items = list(bought_items)
    for item in return_items:
        if 'checked' in item:
            del item['checked']
    return return_items
