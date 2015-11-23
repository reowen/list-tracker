import webapp2
import jinja2
import admin
from google.appengine.ext import ndb

import json
import time

class ManageList(admin.Handler):
    def get(self):
        if not self.user:
            self.redirect('/')
        else:
            params = dict(user = self.user)
            lists = admin.WishList.by_user(self.user.key.id())
            if lists:
                params['lists'] = lists
                self.render('manage-lists.html', **params)
            else:
                params['nolist'] = 'You have no lists to display'
                self.render('manage-lists.html', **params)


class DeleteList(admin.Handler):
    listname = ''
    referer = '/'
    def get(self):
        if not self.user:
            self.redirect('/')
        else:
            list_id = self.request.get('l')
            DeleteList.referer = self.request.headers.get('referer', '/')
            if not list_id:
                self.redirect('/')
            l = admin.WishList.by_id(int(list_id))
            DeleteList.listname = l.listname

            params = dict(user = self.user,
                          list_id = list_id,
                          listname = DeleteList.listname,
                          referer = DeleteList.referer)
            self.render('delete-list.html', **params)
    def post(self):
        delete = self.request.get('delete')
        list_id = self.request.get('l')

        params = dict(user = self.user,
                      list_id = list_id,
                      referer = DeleteList.referer)

        if not list_id:
            params['error'] = 'There was an error processing your request. Return to the home page and try again.'
            self.render('delete-list.html', **params)
            return
        elif delete:
            l_key = admin.WishList.by_id(int(list_id))
            DeleteList.listname = l_key.listname
            group_id = l_key.group
            l_key.key.delete()
            time.sleep(0.1)
            #update user-lists cache
            lists = admin.WishList.by_user(self.user.key.id(), update = True)
            params['lists'] = lists
            #update group-lists cache
            admin.WishList.by_group(group_id, update = True)
            #render confirmation page
            params['delete'] = 'Successfully deleted %s' % DeleteList.listname
            self.render('manage-lists.html', **params)
            return
        else:
            refresh = self.request.path + '?l=%s' % list_id
            self.redirect(refresh)




prompt = """
Start by naming your list.  The list name is what will appear above your list
when other group members view the group, so be sure to use an informative
title (e.g. "Jay's list," "Mary's list," etc..).
<br>
<br>
If you wish to make a list on behalf of another person -- perhaps if he/she does
not have an email address -- be sure to click the checkbox labelled "Make this
list on behalf of another person."  Note that if you check this box, the list
will be associated with your email address, and only you will be able to
modify it.  Checking this box also allows you to see which items in the list
have already been bought, and by whom.
<br>
<br>
For example, if you have a baby named Caroline, and you want to add her list
to the group, you could name your list "Caroline's list," and click the box
"Make this list on behalf of another person."  Then, you would be able to add
or delete items from her list, and also see which items have already been
bought by other group members.
<br>
<br>
"""

class CreateList(admin.Handler):
    numrows = 5
    def get(self):
        if not self.user:
            self.redirect('/login')
        else:
            #numrows specifies length of the input form
            numrows = 5
            group_id = self.request.get('g')
            group = admin.Group.by_id(int(group_id))
            groupname = str(group.groupname)

            header = 'Create list for %s' % groupname
            self.render('create-list.html',
                        user = self.user,
                        header = header,
                        numrows = numrows)

    def post(self):
        #numrows specifies length of input form
        numrows = 5
        #items to be saved to datastore
        items = []
        #list of dicts to pass through jinja template
        render_row = []
        has_error = False
        group_id = self.request.get('g')
        group = admin.Group.by_id(int(group_id))
        groupname = str(group.groupname)
        header = 'Make a new list for %s' % groupname

        params = dict(user = self.user,
                      header = header,
                      numrows = numrows)

        listname = self.request.get('listname')
        if not listname:
            params['error_listname'] = 'Please provide a list name.'
            has_error = True
        elif admin.WishList.by_name(listname, group_id):
            params['error_listname'] = 'This group already has a list with that name.'
            has_error = True
        else:
            params['listname'] = listname

        for row in range(0, numrows):
            item_req = 'item_%s' % row
            item = self.request.get(item_req)

            link_req = 'link_%s' % row
            link = self.request.get(link_req)

            note_req = 'note_%s' % row
            note = self.request.get(note_req)

            if item and valid_item(item):
                if link and not valid_link(link):
                    render_row.append({'item': item,
                                       'link': link,
                                       'note': note,
                                       'error': 'Invalid link. Be sure to include http://..'})
                    has_error = True
                else:
                    items.append({'item': item,
                                  'link': link,
                                  'note': note})
                    render_row.append({'item': item,
                                       'link': link,
                                       'note': note,
                                       'error': ''})

            #if there's a link or note, but no corresponding item
            elif link or note:
                render_row.append({'item': item,
                                   'link': link,
                                   'note': note,
                                   'error': 'Link or note must have a corresponding item.'})
                has_error = True

        other_person = self.request.get('other_person')
        if has_error:
            params['render_row'] = render_row
            params['length'] = len(render_row)

            more = self.request.get('more_items')
            if more:
                params['numrows'] = numrows + 5

            if other_person:
                params['checked'] = 'CHECKED'

            self.render('create-list.html', **params)
            return

        else:
            numitems = len(items)
            params['listname'] = listname
            params['render_row'] = render_row
            params['length'] = len(render_row)
            #be sure to write the new list to the dictionary, using the items
            #dictionary object we defined in this procedure

            more = self.request.get('more_items')
            if more:
                params['numrows'] = numrows + 5
                if other_person:
                    params['checked'] = 'CHECKED'
                self.render('create-list.html', **params)
                return

            if other_person:
                for_other_person = True
                l = admin.WishList.save(listname, self.user.key.id(),
                                        self.user.firstname, group_id,
                                        groupname, items, for_other_person)
                l_key = l.put()
                time.sleep(0.1)
                #update user-lists cache
                admin.WishList.by_user(self.user.key.id(), update = True)
                #update group-lists cache
                admin.WishList.by_group(self.request.get('g'), update = True)

            else:
                l = admin.WishList.save(listname, self.user.key.id(),
                                        self.user.firstname, group_id,
                                        groupname, items)
                l_key = l.put()
                time.sleep(0.1)
                #update user-lists cache
                admin.WishList.by_user(self.user.key.id(), update = True)

            params['create_success'] = 'Successfully created list %s!' % listname
            params['group_id'] = group_id
            params['list_id'] = l_key.id()
            params['confirm_list'] = render_row
            self.render('confirm-list.html', **params)


class EditList(admin.Handler):
    edit_items = []
    def get(self):
        if not self.user:
            self.redirect('/')
        else:
            referer = self.request.headers.get('referer', '/')
            l = self.request.get('l')
            edit_list = admin.WishList.by_id(int(l))
            #by default, list has a group
            groupless = False
            if not edit_list:
                self.render('front.html', user=self.user,
                            text = "It appears that list doesn't exist")
            elif edit_list.groupname == '---groupless---':
                groupless = True

            orig_listname = str(edit_list.listname)
            EditList.edit_items = list(edit_list.items)
            render_row = list(edit_list.items)
            #to specify the length of the existing item list for rendering
            length = len(render_row)
            numrows = length + 5
            params = dict(user = self.user,
                          header = orig_listname,
                          numrows = numrows,
                          edit = True,
                          listname = orig_listname,
                          render_row = render_row,
                          length = length,
                          list_id = l,
                          groupless = groupless)
            if 'create-list' in referer:
                params['create_success'] = 'Successfully created %s for group %s.  If you like, you can make additional edits here.' % (edit_list.listname, edit_list.groupname)

            self.render('edit-list.html', **params)

    def post(self):
        new_items = []
        render_row = []
        # Fix the edit list bug
        l = self.request.get('l')
        l_render = admin.WishList.by_id(int(l))

        length = len(list(l_render.items))
        numrows = length + 5

        has_error = False
        listname = self.request.get('listname')
        params = dict(user = self.user,
                      header = listname,
                      numrows = numrows,
                      edit = True,
                      listname = listname,
                      render_row = render_row,
                      length = length)

        if not listname:
            params['error_listname'] = 'Please provide a list name.'
            has_error = True
        else:
            params['listname'] = listname

        for row in range(0, numrows): #update to range(0, numrows)
            item_req = 'item_%s' % row
            item = self.request.get(item_req)

            link_req = 'link_%s' % row
            link = self.request.get(link_req)

            note_req = 'note_%s' % row
            note = self.request.get(note_req)

            del_req = 'del_%s' % row
            delete = self.request.get(del_req)

            if item and valid_item(item):
                if delete:
                    for e in EditList.edit_items:
                        if e['item'] == item:
                            EditList.edit_items.remove(e)

                elif link and not valid_link(link):
                    render_row.append({'item': item,
                                       'link': link,
                                       'note': note,
                                       'error': 'Invalid link.  Be sure to include http://...'})
                    has_error = True

                else:
                    render_row.append({'item': item,
                                       'link': link,
                                       'note': note,
                                       'error': ''})
            elif link or note:
                render_row.append({'item': item,
                                   'link': link,
                                   'note': note,
                                   'error': 'Link or note must have a corresponding item.'})
                has_error = True

        more = self.request.get('more_items')
        if has_error:
            params['render_row'] = render_row
            params['length'] = len(render_row)
            if more:
                params['numrows'] = len(render_row) + 10
            else:
                params['numrows'] = len(render_row) + 5
            self.render('edit-list.html', **params)
            return

        else:

            params['render_row'] = render_row
            params['length'] = len(render_row)
            if more:
                params['numrows'] = len(render_row) + 10
            else:
                params['numrows'] = len(render_row) + 5

            #update the entries for the database
            new_items = list(EditList.edit_items)
            for row in render_row:
                in_list = False
                for i in new_items:
                    if row['item'] == i['item']:
                        i['note'] = row['note']
                        i['link'] = row['link']
                        in_list = True
                if not in_list:
                    new_items.append({'item': row['item'],
                                      'note': row['note'],
                                      'link': row['link']})

            l = self.request.get('l')
            l_new = admin.WishList.by_id(int(l))
            l_new.listname = self.request.get('listname')
            l_new.items = new_items
            l_new_group_id = l_new.group
            if not l_new.items:
                params['process_error'] = 'There was an error processing your request'
            else:
                l_new.put()
                time.sleep(0.1)
                #update user-lists cache
                admin.WishList.by_user(self.user.key.id(), update = True)
                #update group-lists cache
                admin.WishList.by_group(l_new_group_id, update = True)
                params['success'] = 'Successfully updated your list. %s'

            self.render('edit-list.html', **params)


import re
#item validation
# ITEM_RE = r"[a-zA-Z0-9]$"
# def valid_item(item):
#     return item and bool(re.search(ITEM_RE, item))
def valid_item(item):
    if item.isspace():
        return False
    else:
        return True


#URL validation
URL_RE = re.compile(r'^(?:http|ftp)s?://' # http:// or https://
                    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
                    r'localhost|' #localhost...
                    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
                    r'(?::\d+)?' # optional port
                    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

def valid_link(link):
    return link and URL_RE.match(link)


"""
For editing and viewing lists
"""

def extract_list(items):
    extracted_list = []
    for item in items:
        if 'bought' not in v:
            extracted_list.append({'item': k,
                                   'link': v['link'],
                                   'note': v['note']})
        else:
            extracted_list.append({'item': k,
                                   'link': v['link'],
                                   'note': v['note'],
                                   'bought': v['bought']})
    return extracted_list

def edit_list(name, link, note, item_dict):
    new_dict = list(item_dict)
    for item in item_dict:
        in_list = False
        if item['item'] == name:
            item['link'] = link
            item['note'] = note
            in_list = True
        if not in_list:
            item_dict.append({'item': name,
                              'link': link,
                              'note': note})
    return new_dict

def path_referrer(referrer):
    pos = referrer.find('?')
    return referrer[:pos]
