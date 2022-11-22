# -*- coding: utf-8 -*-
# from odoo import http


# class P21helpdesk(http.Controller):
#     @http.route('/p21helpdesk/p21helpdesk/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/p21helpdesk/p21helpdesk/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('p21helpdesk.listing', {
#             'root': '/p21helpdesk/p21helpdesk',
#             'objects': http.request.env['p21helpdesk.p21helpdesk'].search([]),
#         })

#     @http.route('/p21helpdesk/p21helpdesk/objects/<model("p21helpdesk.p21helpdesk"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('p21helpdesk.object', {
#             'object': obj
#         })
