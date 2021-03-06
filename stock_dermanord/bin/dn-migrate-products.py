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

#pip install odoorpc
# ~/.odoorpc
#[dermanord]
#host = localhost
#protocol = xmlrpc
#user = admin
#timeout = 120
#database = <database>
#passwd = <password>
#type = ODOO
#port = 8069

#pip install odoorpc
import re

try:
    import odoorpc
except ImportError:
    raise Warning('odoorpc library missing, pip install odoorpc')

params = odoorpc.session.get('dermanord')
odoo = odoorpc.ODOO(params.get('host'),port=params.get('port'))

# Check available databases
#print(odoo.db.list())

# Login (the object returned is a browsable record)
#odoo.login(local_database,local_user, local_passwd)
odoo.login(params.get('database'),params.get('user'),params.get('passwd'))

#Convert sizes to be readable as other attributes.
for template_id in odoo.env['product.template'].search([('name', 'like', '%(XS)')]):
    record = odoo.env['product.template'].read(template_id,['name'])
    record['name'] = record['name'][:-4] + ", XS"
    odoo.env['product.template'].write(template_id, record)
for template_id in odoo.env['product.template'].search([('name', 'like', '%(S)')]):
    record = odoo.env['product.template'].read(template_id,['name'])
    record['name'] = record['name'][:-3] + ", S"
    odoo.env['product.template'].write(template_id, record)
for template_id in odoo.env['product.template'].search([('name', 'like', '%(M)')]):
    record = odoo.env['product.template'].read(template_id,['name'])
    record['name'] = record['name'][:-3] + ", M"
    odoo.env['product.template'].write(template_id, record)
for template_id in odoo.env['product.template'].search([('name', 'like', '%(L)')]):
    record = odoo.env['product.template'].read(template_id,['name'])
    record['name'] = record['name'][:-3] + ", L"
    odoo.env['product.template'].write(template_id, record)
for template_id in odoo.env['product.template'].search([('name', 'like', '%(XL)')]):
    record = odoo.env['product.template'].read(template_id,['name'])
    record['name'] = record['name'][:-4] + ", XL"
    odoo.env['product.template'].write(template_id, record)
for template_id in odoo.env['product.template'].search([('name', 'like', '%(XXL)')]):
    record = odoo.env['product.template'].read(template_id,['name'])
    record['name'] = record['name'][:-5] + ", XXL"
    odoo.env['product.template'].write(template_id, record)

#Fetch id of Volume attribute. Create the attribute if it doesn't exist.
volume_id = odoo.env['product.attribute'].search([('name', '=', 'Volume')])
if len(volume_id) < 1:
    volume_id = odoo.env['product.attribute'].create({'name': 'Volume'})
else:
    volume_id = volume_id[0]

print 'Volume attribute id: %s' % volume_id

#Fetch all Volume attribute values
attr_values = []
for id in odoo.env['product.attribute.value'].search([('attribute_id', '=', volume_id)]):
    attr_values.append(odoo.env['product.attribute.value'].read(id, ['name']))

print 'Volume attribute values: %s' % attr_values

#Check if the string describes a volume attribute value
def is_volume_variant(variant):
    pattern = re.compile('\\ *[0-9]+\\ *ml')
    return pattern.match(variant)

# Get attr value, if missing create both product.attribute and product.attribute.value. Change product.attribute afterwards.
def get_attr_value_id(name):
    value_id = odoo.env['product.attribute.value'].search([('name','=',name)])
    #print "get_attr_value_id %s" % value_id
    if not value_id:
        attribute_id = odoo.env['product.attribute'].create({'name': name, })
        value_id = [odoo.env['product.attribute.value'].create({'name': name, 'attribute_id': attribute_id})]
        print "\tCreated new attribute %s" % name
    else:
        print "\tFound existing attribute %s" % name
    #print value_id
    return value_id[0]

#Only process products that match the pattern
pattern = re.compile('^[0-9]{4}\-[0-9]+$')
#for template_id in odoo.env['product.template'].search([('name', 'like', '%,%')])[:20]:
for template_id in odoo.env['product.template'].search([('name', 'like', '%,%'), ('sale_ok','=',1)]): #, ('default_code', 'like', '3029-')]):
    print "processing template id %s" % template_id
    record = odoo.env['product.template'].read(template_id,['name', 'default_code', 'product_variant_ids', 'list_price'])
    attr_name = [x.strip() for x in record['name'].split(',')]
    template_name = attr_name[0].encode('utf-8').strip()  # Template name are the first sentence before coma
    #print template_name
    #Generate list of attribute ids for the product tied to this template
    #These values will change when adding new products to a template, so we need to save them here
    o_attr_ids = []
    for attr in [x.strip() for x in record['name'].split(',')]:
        #print "attribute: %s" % attr.encode('utf-8').strip()
        if not attr.encode('utf-8').strip() == template_name: 
            o_attr_ids.append(get_attr_value_id(attr.encode('utf-8').strip()))
    if record['product_variant_ids'] and record['default_code'] and pattern.match(record['default_code']):
        print "\nTemplate %s -> %s" % (record['name'].encode('utf-8').strip(),template_name)
        lprice = None
        variant_prices = []
        autoprice = True
        #print "tmpl_name: %s code: %s" % (template_name, record['default_code'][:5])
        product_ids = odoo.env['product.product'].search([('name', 'like', '%s,%%' % template_name), ('default_code', 'like', '%s%%' % record['default_code'][:5]), ('sale_ok','=',1)])
        if len(product_ids) > 1:
            for prod_id in product_ids:
                r = odoo.env['product.product'].read(prod_id,['name', 'product_tmpl_id', 'attribute_value_ids', 'default_code', 'lst_price'])
                #~ print r['name']
                #~ print r['id']
                if r['default_code'] and pattern.match(r['default_code']):
                    #~ print "matched"
                    #print "attribute_value_ids %s" % r['attribute_value_ids']
                    attr_ids = []
                    #Check if this is the variant tied to the template
                    if r['default_code'] == record['default_code']:
                        attr_ids = o_attr_ids
                        r['lst_price'] = record['list_price']
                    else:
                        #Generate list of attribute ids
                        for attr in [x.strip() for x in r['name'].split(',')]:
                            #print "attribute: %s" % attr.encode('utf-8').strip()
                            if not attr.encode('utf-8').strip() == template_name: 
                                attr_ids.append(get_attr_value_id(attr.encode('utf-8').strip()))
                    #Create variant pricing data if possible
                    if len(attr_ids) == 1:
                        variant_prices.append((attr_ids[0], r['lst_price']))
                    else:
                        autoprice = False
                    #Create write statement for attribute ids
                    if attr_ids:
                        r['attribute_value_ids'].append((6, 0, attr_ids))
                    r['name'] = template_name
                    r['product_tmpl_id'] = template_id
                    #print "attribute_value_ids %s" % r['attribute_value_ids']
                    #Set price to lowest variant price
                    if lprice != None and lprice < r['lst_price']:
                        r['lst_price'] = lprice
                    else:
                        lprice = r['lst_price']
                    #print "writing"
                    odoo.env['product.product'].write(r['id'], r)
                    #Move BOMs to new template
                    for bom_id in odoo.env['mrp.bom'].search([('product_id', '=', r['id'])]) + odoo.env['mrp.bom'].search([('product_id', '=', r['id']), ('active', '=', False)]):
                        bom = odoo.env['mrp.bom'].read(bom_id, ['product_tmpl_id'])
                        bom['product_tmpl_id'] = record['id']
                        odoo.env['mrp.bom'].write(bom_id, bom)
            #Write variant prices if possible
            if autoprice:
                for t in variant_prices:
                    odoo.env['product.attribute.price'].create({
                        'product_tmpl_id': template_id,
                        'value_id': t[0],
                        'price_extra': t[1] - lprice,
                    })
                print "Automaticly set prices for the %s variants belonging to product.template %s with id %s" % (len(variant_prices), template_name, template_id)
            else:
                print "Manual price fix required for product.template %s with id %s" % (template_name, template_id)
            odoo.env['product.template'].write(template_id, {'name': template_name}) #4838 2040 
#Delete templates without variants
failed_ids = []
for template_id in odoo.env['product.template'].search([('product_variant_ids','=?', None)]):
    try:
        odoo.env['product.template'].unlink([template_id])
    except:
        failed_ids.append(template_id)
if failed_ids:
    print "Cleanup failed. Unable to remove product.template with ids %s" % failed_ids
else:
    print "Cleanup successul. All redundant product.template deleted."
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

