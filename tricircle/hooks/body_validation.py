# Copyright (c) 2015 Mirantis, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_log import log
from oslo_serialization import jsonutils
from pecan import hooks
from neutron_lib.api import attributes
from neutron_lib.api import converters as lib_converters
from neutron_lib.db import constants as db_const
from neutron_lib import exceptions as n_exc

from tricircle.db import constants
from neutron_lib import constants as neutron_lib_const
from neutron_lib.api import validators


import webob.exc
#from neutron.api.v2 import base as v2_base
#from neutron.pecan_wsgi.hooks import utils

LOG = log.getLogger(__name__)

def _validate_destination_cidr_list(data,valid_values=None):
    """Validate a list of unique route destination dicts.

    :returns: None if data is a valid list of unique host route dicts,
    otherwise a human readable message indicating why validation failed.
    """
    if not isinstance(data, list):
        msg = _("Invalid data format for destination_cidr_list: '%s'") % data
        return msg

    expected_keys = ['destination']
    hostroutes = []
    for hostroute in data:
        msg = validators._verify_dict_keys(expected_keys, hostroute)
        if msg:
            return msg
        msg = validators.validate_subnet(hostroute['destination'])
        if msg:
            return msg
        if hostroute in hostroutes:
            msg = _("Duplicate hostroute '%s'") % hostroute
            return msg
        hostroutes.append(hostroute)


validators.add_validator('type:destination_cidr_list', _validate_destination_cidr_list)



TRICIRCLE_RESOURCE = 'tricircle_resource'
TRICIRCLE_RESOURCES = '%ss' % TRICIRCLE_RESOURCE 


CORE_ROUTER = 'core_router'
CORE_ROUTERS = '%ss' % CORE_ROUTER
CORE_ROUTER_INTERFACE = 'core_router_interface'
CORE_ROUTER_INTERFACES = '%ss' % CORE_ROUTER_INTERFACE 

DYNAMIC_PEERING_CONNECTION = 'dynamic_peering_connection'
DYNAMIC_PEERING_CONNECTIONS = '%ss' % DYNAMIC_PEERING_CONNECTION 

FIREWALL_GATEWAY = 'firewall_gateway'
FIREWALL_GATEWAYS = '%ss' % FIREWALL_GATEWAY 

FIREWALL_BYPASS= 'firewall_bypass'
FIREWALL_BYPASSS = '%ss' % FIREWALL_BYPASS 

REGION= 'region'
REGIONS = '%ss' % REGION

DC= 'dc'
DCS = '%ss' % DC

DCI= 'dci'
DCIS = '%ss' % DCI

FABRIC = 'fabric'
FABRICS = '%ss' % FABRIC

ROUTE_ENTRY = 'route_entry'
ROUTE_ENTRYS = '%ss' %ROUTE_ENTRY 

RESOURCE_ATTRIBUTE_MAP = {
    # Region here is not same with openstack region.
    REGIONS: {
        'id': {'allow_post': False, 'allow_put': False,
               'validate': {'type:uuid': None},
               'is_visible': True,
               'primary_key': True},
        'region_name': {'allow_post': True, 'allow_put': False,'required': True,
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE},
                              'is_visible': True},
    },
    DCS: {
        'id': {'allow_post': False, 'allow_put': False,
               'validate': {'type:uuid': None},
               'is_visible': True,
               'primary_key': True},
        'region_id': {'allow_post': True, 'allow_put': False, 'required': True,
               'validate': {'type:uuid': None},
               'is_visible': True},
        'dc_name': {'allow_post': True, 'allow_put': False,'required': True,
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE},
                              'is_visible': True},
    },
    FABRICS: {
        'id': {'allow_post': False, 'allow_put': False,
               'validate': {'type:uuid': None},
               'is_visible': True,
               'primary_key': True},
        'dc_id': {'allow_post': True, 'allow_put': False,'required': True,
               'validate': {'type:uuid': None},
               'is_visible': True},
        #fabric_name is same with openstack region name.
        'fabric_name': {'allow_post': True, 'allow_put': False,'required': True,
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE},
                              'is_visible': True},
    },
    TRICIRCLE_RESOURCES: {
        'id': {'allow_post': True, 'allow_put': False,
               'validate': {'type:uuid': None},
               'is_visible': True,
               'primary_key': True},
        'name': {'allow_post': True, 'allow_put': True,
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE}, 'is_visible': True},
        'region_name': {'allow_post': True, 'allow_put': False,
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE}, 'is_visible': True},
        'project_id': {'allow_post': True, 'allow_put': False,'required': True,
                      'validate': {
                          'type:string': db_const.PROJECT_ID_FIELD_SIZE},
                      'required_by_policy': True,
                      'is_visible': True},
        'resource_type': {'allow_post': True, 'allow_put': False,
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE},
                 'default': '', 'is_visible': True},
        'admin_state_up': {'allow_post': True, 'allow_put': True,
                           'validate': {'type:boolean': None},
                           'default': True,
                           'convert_to': lib_converters.convert_to_boolean,
                           'is_visible': True},
        'status': {'allow_post': True, 'allow_put': True, 'default':"DOWN",
                  'is_visible': True},
    },
    CORE_ROUTER_INTERFACES: {
        'interface_id': {'allow_post': False, 'allow_put': False,
               'validate': {'type:uuid': None},
               'is_visible': True,
               'primary_key': True},
        'project_id': {'allow_post': False, 'allow_put': False,
                      'validate': {
                          'type:string': db_const.PROJECT_ID_FIELD_SIZE},
                      'required_by_policy': True,
                      'is_visible': True},
        'fabric': {'allow_post': True, 'allow_put': False,'required': True,
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE},
                 'is_visible': True},
    },
    CORE_ROUTERS: {
        'id': {'allow_post': False, 'allow_put': False,
               'validate': {'type:uuid': None},
               'is_visible': True,
               'primary_key': True},
        'dc': {'allow_post': True, 'allow_put': False,'required': True,
               'validate': {'type:string': db_const.NAME_FIELD_SIZE},
               'is_visible': True},
        'project_id': {'allow_post': True, 'allow_put': False,'required': True,
                      'validate': {
                          'type:string': db_const.PROJECT_ID_FIELD_SIZE},
                      'required_by_policy': True,
                      'is_visible': True},
        'core_router_name': {'allow_post': True, 'allow_put': True,
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE},
                 'default': '', 'is_visible': True},
        'admin_state_up': {'allow_post': True, 'allow_put': True,
                           'validate': {'type:boolean': None},
                           'default': True,
                           'convert_to': lib_converters.convert_to_boolean,
                           'is_visible': True},
        'description': {'allow_post': True, 'allow_put': True, 
                 'required':False, 'default': '',
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE}, 'is_visible': True},
        'status': {'allow_post': True, 'allow_put': True, 'default':"DOWN",
                  'is_visible': True},
        'routes': {'allow_post': True, 'allow_put': True,
                        'convert_to':
                            lib_converters.convert_none_to_empty_list,
                        'default': neutron_lib_const.ATTR_NOT_SPECIFIED,
                        'validate': {'type:hostroutes': None},
                        'is_visible': True},
    },
    DYNAMIC_PEERING_CONNECTIONS: {
        'dynamic_peering_connection_id': {'allow_post': False, 'allow_put': False,
               'validate': {'type:uuid': None},
               'is_visible': True,
               'primary_key': True},
        'local_router_id': {'allow_post': True, 'allow_put': False,
               'validate': {'type:uuid': None},
               'is_visible': True},
        'peering_router_id': {'allow_post': True, 'allow_put': False,
               'validate': {'type:uuid': None},
               'is_visible': True},
        'project_id': {'allow_post': True, 'allow_put': False,'required': True,
                      'validate': {
                          'type:string': db_const.PROJECT_ID_FIELD_SIZE},
                      'required_by_policy': True,
                      'is_visible': True},
        'dynamic_peering_connection_name': {'allow_post': True, 'allow_put': True,
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE},
                 'default': '', 'is_visible': True},
        'admin_state_up': {'allow_post': True, 'allow_put': True,
                           'validate': {'type:boolean': None},
                           'default': True,
                           'convert_to': lib_converters.convert_to_boolean,
                           'is_visible': True},
        'description': {'allow_post': True, 'allow_put': True, 
                 'required':False, 'default': '',
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE}, 'is_visible': True},
        'status': {'allow_post': False, 'allow_put': False, 'default':"DOWN",
                  'is_visible': True},
    },
    DCIS: {
        'fabric': {'allow_post': True, 'allow_put': False,'required': True,
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE},
                 'is_visible': True},
        'router_id': {'allow_post': True, 'allow_put': False,'required': True,
               'validate': {'type:uuid': None},
               'is_visible': True},
        'dci_peering_id': {'allow_post': True, 'allow_put': False,'required': True,
               'validate': {'type:uuid': None},
               'is_visible': True},
        'project_id': {'allow_post': True, 'allow_put': False,'required': True,
                      'validate': {
                          'type:string': db_const.PROJECT_ID_FIELD_SIZE},
                      'required_by_policy': True,
                      'is_visible': True},
        'type':{'allow_post': True, 'allow_put': False, 'required': True,
                  'is_visible': True},
        'name': {'allow_post': True, 'allow_put': True,
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE},
                 'default': '', 'is_visible': True},
        'admin_state_up': {'allow_post': True, 'allow_put': True,
                           'validate': {'type:boolean': None},
                           'default': True,
                           'convert_to': lib_converters.convert_to_boolean,
                           'is_visible': True},
        'description': {'allow_post': True, 'allow_put': True, 
                 'required':False, 'default': '',
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE}, 'is_visible': True},
        'status': {'allow_post': True, 'allow_put': True, 'default':"DOWN",
                  'is_visible': True},
    },
    FIREWALL_GATEWAYS: {
        'id': {'allow_post': False, 'allow_put': False,
               'validate': {'type:uuid': None},
               'is_visible': True,
               'primary_key': True},
        'fabric': {'allow_post': True, 'allow_put': False,'required': True,
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE},
                 'is_visible': True},
        'firewall_id': {'allow_post': True, 'allow_put': False,'required': True,
               'validate': {'type:uuid': None},
               'is_visible': True},
        'router_id': {'allow_post': True, 'allow_put': False,'required': True,
               'validate': {'type:uuid': None},
               'is_visible': True},
        'project_id': {'allow_post': True, 'allow_put': False,'required': True,
                      'validate': {
                          'type:string': db_const.PROJECT_ID_FIELD_SIZE},
                      'required_by_policy': True,
                      'is_visible': True},
        'admin_state_up': {'allow_post': True, 'allow_put': True,
                           'validate': {'type:boolean': None},
                           'default': True,
                           'convert_to': lib_converters.convert_to_boolean,
                           'is_visible': True},
        'description': {'allow_post': True, 'allow_put': True, 
                 'required':False, 'default': '',
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE}, 'is_visible': True},
        'status': {'allow_post': True, 'allow_put': True, 'default':"DOWN",
                  'is_visible': True},
    },
    FIREWALL_BYPASSS: {
        'id': {'allow_post': False, 'allow_put': False,
               'validate': {'type:uuid': None},
               'is_visible': True,
               'primary_key': True},
        'fabric': {'allow_post': True, 'allow_put': False,'required': True,
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE},
                 'is_visible': True},
        'core_router_id': {'allow_post': True, 'allow_put': False,'required': True,
               'validate': {'type:uuid': None},
               'is_visible': True},
        'router_id': {'allow_post': True, 'allow_put': False,'required': True,
               'validate': {'type:uuid': None},
               'is_visible': True},
        'project_id': {'allow_post': True, 'allow_put': False,'required': True,
                      'validate': {
                          'type:string': db_const.PROJECT_ID_FIELD_SIZE},
                      'required_by_policy': True,
                      'is_visible': True},
        'admin_state_up': {'allow_post': True, 'allow_put': True,
                           'validate': {'type:boolean': None},
                           'default': True,
                           'convert_to': lib_converters.convert_to_boolean,
                           'is_visible': True},
        'description': {'allow_post': True, 'allow_put': True, 
                 'required':False, 'default': '',
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE}, 'is_visible': True},
        'status': {'allow_post': True, 'allow_put': True, 'default':"DOWN",
                  'is_visible': True},
    },
    ROUTE_ENTRYS: {
        'id': {'allow_post': False, 'allow_put': False,
               'validate': {'type:uuid': None},
               'is_visible': True,
               'primary_key': True},
        'src_router': {'allow_post': True, 'allow_put': False,'required': True,
               'validate': {'type:uuid': None},
               'is_visible': True},
        'nxt_router': {'allow_post': True, 'allow_put': False,'required': True,
               'validate': {'type:uuid': None},
               'is_visible': True},
        'project_id': {'allow_post': True, 'allow_put': False,'required': True,
                      'validate': {
                          'type:string': db_const.PROJECT_ID_FIELD_SIZE},
                      'required_by_policy': True,
                      'is_visible': True},
        'admin_state_up': {'allow_post': True, 'allow_put': True,
                           'validate': {'type:boolean': None},
                           'default': True,
                           'convert_to': lib_converters.convert_to_boolean,
                           'is_visible': True},
        'description': {'allow_post': True, 'allow_put': True, 
                 'required':False, 'default': '',
                 'validate': {'type:string': db_const.NAME_FIELD_SIZE}, 'is_visible': True},
        'status': {'allow_post': True, 'allow_put': True, 'default':"DOWN",
                  'is_visible': True},
        'destination_cidr_list': {'allow_post': True, 'allow_put': True,
                        'convert_to':
                            lib_converters.convert_none_to_empty_list,
                        'default': neutron_lib_const.ATTR_NOT_SPECIFIED,
                        'validate': {'type:destination_cidr_list': None},
                        'is_visible': True},
    }
}

class BodyValidationHook(hooks.PecanHook):

    priority = 120

    def before(self, state):
        if state.request.method not in ('POST', 'PUT'):
            print "MaXiao method is not POST/PUT"
            return
        print "MaXiao Test BodyValidationHook"
        resource = state.request.context.get('resource')
        resources= '%ss' % resource 

        print "MaXiao Controller Resource is "+str(resource)
        is_create = state.request.method == 'POST'
        if not resource:
            return

        try:
            json_data = jsonutils.loads(state.request.body)
            state.request.context['request_data'] = json_data
            print "MaXiao json_data is "+str(json_data)
        except ValueError:
            LOG.debug("No JSON Data in %(method)s request for %(resource)s",
                      {'method': state.request.method,
                       'resource': resource})
            msg = "No body "+str(resource)+" find."
            raise webob.exc.HTTPBadRequest(msg)
            return
        if not (resource in json_data):
            LOG.info("No JSON Data in %(method)s request for %(resource)s",
                      {'method': state.request.method,
                       'resource': resource})
            # there is no resource in the request. 
            msg = "No body "+str(resource)+" find."
            raise webob.exc.HTTPBadRequest(msg)
            return
        attr_info = RESOURCE_ATTRIBUTE_MAP.get(resources)
        if not attr_info:
            return
        print "MaXiao attr_info is "+str(attr_info)
        data = BodyValidationHook.check_request_body(json_data,is_create,resource,attr_info)
        state.request.context['resources'] = resources


    @staticmethod
    def check_request_body(body, is_create, resource, attr_info):
        res_dict = body.get(resource)
        attr_ops = attributes.AttributeInfo(attr_info)
        print "MaXiao res_dict is "+str(res_dict)
        
        #verify only check if exist not check valid
        attr_ops.verify_attributes(res_dict)
        print "MaXiao res_dict is "+str(res_dict)
        try: 
            attr_ops.convert_values(res_dict, exc_cls=webob.exc.HTTPBadRequest)
        except n_exc.InvalidInput as e:
            msg = str(e)
            raise webob.exc.HTTPBadRequest(msg)
        print "MaXiao after convert res_dict is "+str(res_dict)
        if is_create:  # POST
            attr_ops.fill_post_defaults(
                res_dict, exc_cls=webob.exc.HTTPBadRequest)
            for attr, attr_vals in attr_info.items():
                print "MaXiao attr is "+str(attr)
                print "MaXiao attr_vals is "+str(attr_vals)
                if attr is 'type' and attr in res_dict:
                    if res_dict['type'] not in ['in','out']: 
                        msg = 'Field type is not right'
                        raise webob.exc.HTTPBadRequest(msg)
                if attr is 'status' and attr in res_dict:
                    if res_dict['status'] not in ['DOWN','ACTIVE','BUILD','ERROR']:
                        msg = 'Field status not right'
                        raise webob.exc.HTTPBadRequest(msg)
            return body
        else:  # PUT
            for attr, attr_vals in attr_info.items():
                print "MaXiao attr is "+str(attr)
                print "MaXiao attr_vals is "+str(attr_vals)
                if attr is 'type' and attr in res_dict:
                    if res_dict['type'] != 'in' and res_dict['type'] != 'out':
                        msg = 'Field type is not in or out'
                        raise webob.exc.HTTPBadRequest(msg)
                if attr is 'status' and attr in res_dict:
                    if res_dict['status'] not in ['DOWN','ACTIVE','BUILD','ERROR']:
                        msg = 'Field status not right'
                        raise webob.exc.HTTPBadRequest(msg)
                if attr in res_dict and not attr_vals['allow_put']:
                    msg = "Cannot update read-only attribute %s" % attr
                    raise webob.exc.HTTPBadRequest(msg)
        print "MaXiao res_dict is 1 "+str(res_dict)
        attr_ops.convert_values(res_dict, exc_cls=webob.exc.HTTPBadRequest)
        print "MaXiao res_dict is 2"+str(res_dict)
        return body
