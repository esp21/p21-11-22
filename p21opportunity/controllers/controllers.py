# -*- coding: utf-8 -*-
# from odoo import http


# class Testmodule01(http.Controller):
#     @http.route('/testmodule01/testmodule01/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/testmodule01/testmodule01/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('testmodule01.listing', {
#             'root': '/testmodule01/testmodule01',
#             'objects': http.request.env['testmodule01.testmodule01'].search([]),
#         })

#     @http.route('/testmodule01/testmodule01/objects/<model("testmodule01.testmodule01"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('testmodule01.object', {
#             'object': obj
#         })
