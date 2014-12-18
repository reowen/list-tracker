import jinja2
import webapp2


import pages
import users
import lists
import groups

app = webapp2.WSGIApplication([('/', pages.MainPage),
                               ('/signup', users.Signup),
                               ('/login', users.Login),
                               ('/logout', users.Logout),
                               ('/signup/welcome', pages.Welcome),
                               ('/groups', pages.GroupPage),
                               ('/my-groups', pages.MyGroups),
                               ('/my-groups/join-group', groups.JoinGroup),
                               ('/my-groups/find-group', groups.FindGroup),
                               ('/my-groups/leave-group', groups.LeaveGroup),
                               ('/my-groups/create-group', groups.CreateGroup),
                               ('/my-groups/invite-to-group', groups.InviteToGroup),
                               ('/my-groups/remove-member', groups.RemoveMember),
                               ('/create-list', lists.CreateList),
                               ('/delete-list', lists.DeleteList),
                               ('/edit-list', lists.EditList),
                               ('/manage-list', lists.ManageList),
                               ('/account-management', pages.ManageAccount),
                               ('/account-management/change-email', users.ChangeEmail),
                               ('/account-management/change-password', users.ChangePassword),
                               ('/z55GjR9J964bW7trF3PkezxRCdRTn6lmvAefieXX', users.ResetPassword),
                               ('/see-members', pages.GroupMembers)
                               ], debug=True)
