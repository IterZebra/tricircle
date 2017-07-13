# Copyright (c) 2015 Huawei Tech. Co., Ltd.
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

import netaddr
import pecan
from pecan import expose
from pecan import Response
from pecan import rest

from pecan import request

import oslo_db.exception as db_exc
from oslo_log import log as logging
from oslo_utils import uuidutils
from  tricircle.api.controllers import uuid_utils
import tricircle.common.context as t_context
import tricircle.common.exceptions as t_exceptions
from tricircle.common.i18n import _
from tricircle.common import policy

from tricircle.db import api as db_api
from tricircle.db import core
from tricircle.db import models
from tricircle.hooks import body_validation
from neutron_lib.api import validators
from neutron.common import utils as common_utils
from tricircle.common import utils
from tricircle.common import return_message as m
from tricircle.api.controllers import firewall_gateway
from tricircle.api.controllers import firewall_bypass
from tricircle.api.controllers import route_entry

LOG = logging.getLogger(__name__)


class CoreRouterInterfaceController(rest.RestController):

    _custom_actions = {
        'add_router_interface': ['PUT'],
        'remove_router_interface': ['PUT'],
    }

    def __init__(self,core_router_id):
        self.core_router_id = core_router_id
        self.resource = "core_router_interfaces"

    @expose(generic=True, template='json')
    def add_router_interface(self):
        context = t_context.extract_context_from_environ()
        body = {"core_router_interface":request.context['request_data']}
        attr_info = body_validation.RESOURCE_ATTRIBUTE_MAP.get(self.resource)
        body_validation.BodyValidationHook.check_request_body(body, True, "core_router_interface", attr_info)
        fabric = request.context['request_data']['fabric']
        _uuid = uuidutils.generate_uuid()
        try:
            with context.session.begin():
                core_router_object = core.get_resource_object(context, models.CoreRouter, self.core_router_id)
                new_core_router_interface = core.create_resource(
                    context, models.CoreRouterInterface,
                    {'interface_id':_uuid,
                     'project_id':core_router_object.project_id,
                     'core_router_id': self.core_router_id,
                     'fabric':fabric,
                    })
        except t_exceptions.ResourceNotFound as e:
            LOG.exception('Failed to add core_router_interface : '
                          'core_router_id %(core_router_id)s ,'
                          '%(exception)s ',
                           {'core_router_id':self.core_router_id,
                            'exception': e})
            return m.CoreRouterNotFound(core_router_id=self.core_router_id).to_dict()
        except db_exc.DBDuplicateEntry as e1:
            LOG.exception('Failed to create core_router_interface :'
                          'core_router_id: %(core_router_id)s,'
                          'fabric: %(fabric)s,'
                          '%(exception)s ',
                          {'core_router_id': self.core_router_id,
                           'fabric': fabric,
                           'exception': e1})
            return_object = m.CoreRouterInterfaceForFabricExists(fabric=fabric)
            return return_object.to_dict()
        except Exception as e2:
            LOG.exception('Failed to create core_router_interface :'
                          'core_router_id: %(core_router_id)s,'
                          'fabric: %(fabric)s,'
                          '%(exception)s ',
                          {'core_router_id': self.core_router_id,
                           'fabric':fabric, 
                           'exception': e2})
            return_object = m.FailureMessage()
            return return_object.to_dict()

        return_object = m.SuccessMessage(result={'core_router_interface': new_core_router_interface})
        return return_object.to_dict()

    @expose(generic=True, template='json')
    def remove_router_interface(self):
        context = t_context.extract_context_from_environ()
        body = {"core_router_interface":request.context['request_data']}
        attr_info = body_validation.RESOURCE_ATTRIBUTE_MAP.get(self.resource)
        body_validation.BodyValidationHook.check_request_body(body, True, "core_router_interface", attr_info)
        fabric= request.context['request_data']['fabric']
        try:
            with context.session.begin():
                core.get_resource(context, models.CoreRouter, self.core_router_id)
                interface_filters = [{'key': 'core_router_id','comparator':'eq','value':self.core_router_id},
                                  {'key': 'fabric','comparator':'eq','value':fabric}]
                interfaces = core.query_resource(context, models.CoreRouterInterface, interface_filters,[])
                if (not len(interfaces)>0):
                    raise t_exceptions.CoreRouterInterfaceDeleteNotFound(core_router_id=self.core_router_id,
                                             fabric=fabric)
                core.delete_resources(context, models.CoreRouterInterface, interface_filters)
                return_object = m.SuccessMessage(result={})
                return return_object.to_dict()
        except t_exceptions.ResourceNotFound as e:
            LOG.exception('Failed to delete core_router_interface : '
                          'core_router_id %(core_router_id)s ,'
                          '%(exception)s ',
                           {'core_router_id':self.core_router_id,
                            'exception': e})
            return m.CoreRouterNotFound(core_router_id=self.core_router_id).to_dict()
        except t_exceptions.CoreRouterInterfaceDeleteNotFound:
            return m.CoreRouterInterfaceNotFound(core_router_id=self.core_router_id,fabric=fabric).to_dict()
        except Exception as e:
            LOG.exception('Failed to delete core_router_interface :'
                          'core_router_id: %(core_router_id)s,'
                          'fabric: %(fabric)s,'
                          '%(exception)s ',
                          {'core_router_id': self.core_router_id,
                           'fabric':fabric, 
                           'exception': e})
            return_object = m.FailureMessage()
            return return_object.to_dict()

class CoreRoutersController(rest.RestController):

    def __init__(self):

        self.sub_controllers = {
            "firewall_gateways": firewall_gateway.FirewallGatewaysController(),
            "firewall_bypasss": firewall_bypass.FirewallBypasssController(),
            "route_entries": route_entry.RouteEntrysController()
        }

        for name, ctrl in self.sub_controllers.items():
            setattr(self, name, ctrl)

    @pecan.expose()
    def _lookup(self, core_router_id, *remainder):
        if remainder and not remainder[-1]:
            remainder = remainder[:-1]
        if uuid_utils.is_uuid_like(core_router_id):
            request.context['resource'] = "core_router_interface"
            return CoreRouterInterfaceController(core_router_id), remainder
        if core_router_id== 'firewall_gateways':
            request.context['resource'] = "firewall_gateway"
            return self.firewall_gateways,remainder
        if core_router_id== 'firewall_bypasss':
            request.context['resource'] = "firewall_bypass"
            return self.firewall_bypasss,remainder
        if core_router_id== 'route_entry':
            request.context['resource'] = "route_entry"
            return self.route_entries,remainder
        else:
            msg = "URL not found "
            raise webob.exc.HTTPBadRequest(msg)

    def filter_to_str(self, value):
        if isinstance(value, list):
            return [str(val) for val in value]
        return str(value)

    def _get_routes_by_core_router_id(self, context ,core_router_id):
        print 'MaXiao _get_routes_by_core_router_id '+str(core_router_id)
        route_filters = [{'key': 'core_router_id','comparator':'eq','value':core_router_id}]
        print 'MaXiao _get_routes_by_core_router_id '+str(core_router_id)
        return core.query_resource(context, models.CoreRouterRoute,route_filters,[])


    def _update_core_router_routes(self, context, core_router_id, core_router):
        try:
            with context.session.begin(subtransactions=True):
                def _combine(ht):
                    return "{}_{}".format(ht['destination'], ht['nexthop'])
        
                old_route_list = self._get_routes_by_core_router_id(context, core_router_id)
        
                new_route_set = set([_combine(route)
                                     for route in core_router['routes']])
        
                old_route_set = set([_combine(route)
                                     for route in old_route_list])
        
                new_routes = []
                for route_str in old_route_set - new_route_set:
                    for route in old_route_list:
                        if _combine(route) == route_str:
                            destination=self.filter_to_str(common_utils.AuthenticIPNetwork(route_str.partition("_")[0]))
                            nexthop=self.filter_to_str(netaddr.IPAddress(route_str.partition("_")[2]))
                            route_filters = [{'key': 'core_router_id','comparator':'eq','value':core_router_id},
                                              {'key': 'destination','comparator':'eq','value':destination},
                                              {'key': 'nexthop','comparator':'eq','value':nexthop}]
                            core.delete_resources(context, models.CoreRouterRoute, route_filters)
                for route_str in new_route_set - old_route_set:
                    destination=self.filter_to_str(common_utils.AuthenticIPNetwork(route_str.partition("_")[0]))
                    nexthop=self.filter_to_str(netaddr.IPAddress(route_str.partition("_")[2]))
                    new_core_routerroute = core.create_resource(
                        context, models.CoreRouterRoute,
                        {'core_router_id': core_router_id,
                          'destination':destination,
                          'nexthop':nexthop})
                 
                for route_str in new_route_set:
                    new_routes.append(
                        {'destination': route_str.partition("_")[0],
                         'nexthop': route_str.partition("_")[2]})
                del core_router["routes"]
                return new_routes
        except Exception as e:
            LOG.exception('Failed to update core_routerroute : '
                          'core_router_id %(core_router_id)s: '
                          '%(exception)s',
                          {'core_router_id': core_router_id,
                           'exception': e})
            raise t_exceptions.CoreRouterRoutesUpdateException()     
 

    def _create_routerroutes(self,context,core_router_id,routes):
        destination = None
        nexthop = None
        try:
            with context.session.begin(subtransactions=True):
                for rt in routes:
                    destination=self.filter_to_str(common_utils.AuthenticIPNetwork(rt['destination']))
                    nexthop=self.filter_to_str(netaddr.IPAddress(rt['nexthop']))
                    new_core_routerroute = core.create_resource(
                        context, models.CoreRouterRoute,
                        {'core_router_id': core_router_id,
                         'destination':destination,
                         'nexthop':nexthop})
        except db_exc.DBDuplicateEntry as e1:
            LOG.exception('Record core_routerroute already exists : '
                          'core_router_id %(core_router_id)s: '
                          'destination%(destination)s: '
                          'nexthop%(nexthop)s: '
                          '%(exception)s',
                          {'core_router_id': core_router_id,
                           'destination':destination,
                           'nexthop':nexthop,
                           'exception': e1})

            raise t_exceptions.CoreRouterRoutesCreateException()
        except Exception as e2:
            LOG.exception('Failed to create core_routerroute : '
                          'core_router_id %(core_router_id)s: '
                          'destination%(destination)s: '
                          'nexthop%(nexthop)s: '
                          '%(exception)s',
                          {'core_router_id': core_router_id,
                           'destination':destination,
                           'nexthop':nexthop,
                           'exception': e2})
            raise t_exceptions.CoreRouterRoutesCreateException()


    @expose(generic=True, template='json')
    def post(self, **kw):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_CREATE):
            pecan.abort(401, _('Unauthorized to create core_router'))
            return

        core_router = request.context['request_data']['core_router']
        _uuid = uuidutils.generate_uuid()
        dc = core_router.get('dc')
        project_id= core_router.get('project_id', '').strip()
        core_router_name = core_router.get('core_router_name', '').strip()
        admin_state_up = core_router.get('admin_state_up',True)
        status = core_router.get('status',"DOWN")
        description = core_router.get('description', '').strip()

        routes= core_router.get('routes')
        try:
            with context.session.begin():
                new_core_router = core.create_resource(
                    context, models.CoreRouter,
                    {'id': _uuid,
                     'dc':dc,
                     'project_id':project_id,
                     'core_router_name':core_router_name,
                     'admin_state_up':admin_state_up,
                     'status':status,
                     'description':description})
    
                if validators.is_attr_set(routes):
                    self._create_routerroutes(context,_uuid,routes)
                new_core_router = core.get_resource(context, models.CoreRouter, _uuid)
            return_object = m.SuccessMessage(result={'core_router': new_core_router})
            return return_object.to_dict()
        except db_exc.DBDuplicateEntry as e1:
            LOG.exception('Record core_router already exists for '
                          'dc %(dc)s: '
                          '%(exception)s',
                          {'dc': dc,
                           'exception': e1})

            return_object = m.CoreRouterForDCExists(dc=dc)
            return return_object.to_dict()
        except Exception as e2:
            LOG.exception('Failed to create core_router : '
                          'dc: %(dc)s,'
                          'project_id %(project_id)s: '
                          'core_router_name: %(core_router_name)s,'
                          '%(exception)s ',
                           {'dc': dc,
                           'project_id': project_id,
                           'core_router_name':core_router_name,
                           'exception': e2})
            return_object = m.FailureMessage()
            return return_object.to_dict()

    @expose(generic=True, template='json')
    def put(self, _id, **kw):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_CREATE):
            pecan.abort(401, _('Unauthorized to put core_router'))
            return

        core_router = request.context['request_data']['core_router']
        try:
            with context.session.begin():
                core.get_resource(context, models.CoreRouter, _id)
                if 'routes' in core_router:
                    self._update_core_router_routes(context, _id, core_router)
                router_updated = core.update_resource(
                    context,models.CoreRouter, _id, core_router)
            return_object = m.SuccessMessage(result={'core_router': router_updated})
            return return_object.to_dict()
        except t_exceptions.ResourceNotFound as e:
            LOG.exception('Failed to update core_router : '
                          'core_router_id %(core_router_id)s ,'
                          '%(exception)s ',
                           {'core_router_id':_id,
                            'exception': e})
            return m.CoreRouterNotFound(core_router_id=_id).to_dict()
        except Exception as e:
            LOG.exception('Failed to update core_router : '
                          '%(exception)s ', {'exception': e})
            return_object = m.FailureMessage()
            return return_object.to_dict()

    @expose(generic=True, template='json')
    def get_one(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_SHOW):
            pecan.abort(401, _('Unauthorized to show core_router'))
            return

        try:
            core_router = db_api.get_core_router(context, _id)
            return_object = m.SuccessMessage(result={'core_router': core_router})
            return return_object.to_dict()
        except t_exceptions.ResourceNotFound as e:
            LOG.exception('Failed to get core_router : '
                          'core_router_id %(core_router_id)s ,'
                          '%(exception)s ',
                           {'core_router_id':_id,
                           'exception': e})
            return m.CoreRouterNotFound(core_router_id=_id).to_dict()

    @expose(generic=True, template='json')
    def get_all(self):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_LIST):
            pecan.abort(401, _('Unauthorized to list core_routers'))
            return

        try:
            core_routers = db_api.list_core_routers(context)
            return_object = m.SuccessMessage(result={'core_routers': core_routers})
            return return_object.to_dict()
        except Exception as e:
            LOG.exception('Failed to list all core_routers : '
                          '%(exception)s ', {'exception': e})
            return_object = m.FailureMessage()
            return return_object.to_dict()

    @expose(generic=True, template='json')
    def delete(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_DELETE):
            pecan.abort(401, _('Unauthorized to delete core_router'))
            return

        try:
            with context.session.begin():
                core_router_object = core.get_resource_object(context, models.CoreRouter, _id)
                if len(core_router_object.interfaces) >0:
                    raise t_exceptions.CoreRouterInUseInterfacesException(core_router_id=_id,
                         count=len(core_router_object.interfaces))
                if len(core_router_object.firewall_bypasss) >0:
                    raise t_exceptions.CoreRouterInUseFirewallBypasssException(core_router_id=_id,
                        count=len(core_router_object.firewall_bypasss))
                core.delete_resource(context, models.CoreRouter, _id)
                return_object = m.SuccessMessage(result={})
                return return_object.to_dict()
        except t_exceptions.ResourceNotFound as e:
            LOG.exception('Failed to delete core_router : '
                          'core_router_id %(core_router_id)s ,'
                          '%(exception)s ',
                           {'core_router_id':_id,
                           'exception': e})
            return m.CoreRouterNotFound(core_router_id=_id).to_dict()
        except t_exceptions.CoreRouterInUse as e:
            LOG.exception('Failed to delete core_router: '
                          '%(core_router_id)s,'
                          '%(exception)s',
                          {'core_router_id': _id,
                           'exception': e})
            return_object = m.CoreRouterInUse(str(e))
            return return_object.to_dict()
        except Exception as e:
            LOG.exception('Failed to delete core_router: '
                          '%(core_router_id)s,'
                          '%(exception)s',
                          {'core_router_id': _id,
                           'exception': e})
            return_object = m.FailureMessage()
            return return_object.to_dict()
