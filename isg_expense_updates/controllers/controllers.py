# -*- coding: utf-8 -*-
from odoo import http

# class IsgExpenseUpdates(http.Controller):
#     @http.route('/isg_expense_updates/isg_expense_updates/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/isg_expense_updates/isg_expense_updates/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('isg_expense_updates.listing', {
#             'root': '/isg_expense_updates/isg_expense_updates',
#             'objects': http.request.env['isg_expense_updates.isg_expense_updates'].search([]),
#         })

#     @http.route('/isg_expense_updates/isg_expense_updates/objects/<model("isg_expense_updates.isg_expense_updates"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('isg_expense_updates.object', {
#             'object': obj
#         })