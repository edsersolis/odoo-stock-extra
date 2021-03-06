#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2016- Vertel AB (<http://vertel.se>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

# sudo pip install -U erppeek
# http://wirtel.be/posts/2014/06/13/using_erppeek_to_discuss_with_openerp/
# http://erppeek.readthedocs.org/

import erppeek

def print_utf8(input):
    print input.encode('utf-8')
print_utf8("Delete all stock.quant in 8.0 before running this script!")
#db_new = erppeek.Client.from_config('local')
#db_new = erppeek.Client.from_config('test')
db_new = erppeek.Client.from_config('eightzero')
#db_old = erppeek.Client.from_config('sixone')
db_old = erppeek.Client.from_config('sixonetunnel')
#Find all internal locations, except for scrap
#internal_location_ids = db_new.model('stock.location').search() #[('usage', '=', 'internal'), ('location_id', '!=', 3)])

# 1) hitta WH / Plocklager  och WH / Plocklager / Kallager spara i variabler
# 2) skapa WH / Plocklager / allm och WH / Plocklager / Kallager / allm  spara i variabler
# stock.location ('usage','=','internal'),()['&',('name','=','Plocklager'),('location_id','=',wh_id)]

wh_id = db_new.model('stock.location').search([('name', '=', 'WH')])[0]
plocklager_id = db_new.model('stock.location').search(['&', ('location_id', '=', wh_id), ('name', '=', 'Plocklager')])[0]
kallager_id = db_new.model('stock.location').search(['&', ('location_id', '=', plocklager_id), ('name', '=', 'Kallager')])[0]
print 'WH_id: %s\nPlocklager_id: %s\nKallager_id: %s' %(wh_id, plocklager_id, kallager_id)

if len(db_new.model('stock.location').search(['&', ('location_id', '=', plocklager_id), ('name', '=', 'allm')])) == 0:
    plocklager_allm = db_new.model('stock.location').create({'name': 'allm', 'location_id': plocklager_id,}).id

else:
    plocklager_allm = db_new.model('stock.location').search(['&', ('location_id', '=', plocklager_id), ('name', '=', 'allm')])[0]

if len(db_new.model('stock.location').search(['&', ('location_id', '=', kallager_id), ('name', '=', 'allm')])) == 0:
    kallager_allm = db_new.model('stock.location').create({'name': 'allm', 'location_id': kallager_id,}).id

else:
    kallager_allm = db_new.model('stock.location').search(['&', ('location_id', '=', kallager_id), ('name', '=', 'allm')])[0]

# Null qty in new database
# radera alla stock.quant  testa unlink först |db_new.execute('delete from stock.quant')

#Check if any stock.quant remains
q_ids = db_new.model('stock.quant').search()
if len(q_ids) > 0:
    print_utf8('Failed to delete stock.quant with ids: %s' % q_ids)
    exit()
else:
    print_utf8('Success! All stock.quant deleted!')
    
# Uppdatera lagersaldo och lagerplats
for prod_o in db_old.model('product.product').read(db_old.model('product.product').search(), ['default_code', 'name', 'qty_available']):
    prod_ids = db_new.model('product.product').search([('default_code','=',prod_o['default_code'])])
    if not prod_ids:
        print_utf8("ERROR: Product not found! name: %s , default_code: %s" % (prod_o['name'], prod_o['default_code']))
    else:
        prod_n = db_new.model('product.product').read(prod_ids, ['id', 'name'])[0]
        #print "to check %s" % prod_o.default_code
        print_utf8('Processing %s' % prod_n['name'])

        move = None
        try:
            move = db_old.model('stock.move').browse([db_old.model('stock.move').search([('product_id','=',prod_o['id'])],order='date desc')[0]])[0]
            #Change to full name
            if move.location_id.usage == 'internal':
                location_name = move.location_id.name
                parent_name = move.location_id.location_id.name
            else:
                location_name = move.location_dest_id.name
                parent_name = move.location_dest_id.location_id.name
            print_utf8("\tOld location: %s" % location_name)
            #print move.name,move.location_id.name,move.location_id.location_id.name,move.location_id.location_id.id
            parent_id = db_new.model('stock.location').search([('name','=', parent_name)])
            #print 'parent',parent_id
            if parent_id:
                parent_id = parent_id[0]
                location_id = db_new.model('stock.location').search(['&', ('name', '=', location_name) ,('location_id','=',parent_id)])[0]
            else:
                location_id = db_new.model('stock.location').search([('name', '=', location_name)])[0]
            # om location_id == plocklager / kallager -> allm
            if location_id == plocklager_id:
                location_id = plocklager_allm
            elif location_id == kallager_id:
                location_id = kallager_allm
            #Change to full name
            print_utf8("\tNew location: %s" % db_new.model('stock.location').browse([location_id])[0].name)
            #~ stock = db_new.model('stock.quant').create({
                    #~ 'product_id' : prod_n['id'],
                    #~ 'qty': prod_o['qty_available'],
                    #~ 'location_id': location_id,
            #~ })
            stock = db_new.model('stock.change.product.qty').create({
                'product_id' : prod_n['id'],
                'new_quantity': prod_o['qty_available'],
                'location_id' : location_id,
            })
            stock.change_product_qty()
        except:
            print_utf8('ERROR: unable to find old location')
        # Check
        prod_n = db_new.model('product.product').read(prod_ids, ['id', 'name', 'qty_available'])[0]
        if not prod_o['qty_available'] == prod_n['qty_available']:
            print_utf8('Check error %s | old count: %s | new count: %s' % (prod_o['name'], prod_o['qty_available'], prod_n['qty_available']))
        else:
            print_utf8('Check passed %s | old count: %s | new count: %s' % (prod_o['name'], prod_o['qty_available'], prod_n['qty_available']))
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
