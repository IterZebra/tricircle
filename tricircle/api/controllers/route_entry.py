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
from tricircle.common import return_message as m
from tricircle.db import api as db_api
from tricircle.db import core
from tricircle.db import models
from tricircle.hooks import body_validation
from neutron_lib.api import validators
from neutron.common import utils as common_utils

from tricircle.common import utils

LOG = logging.getLogger(__name__)

class RouteEntrysController(rest.RestController):

    def filter_to_str(self, value):
        if isinstance(value, list):
            return [str(val) for val in value]
        return str(value)

    def _get_destination_cidrs_by_route_entry_id(self, context ,route_entry_id):
        route_filters = [{'key': 'route_entry_id','comparator':'eq','value':route_entry_id}]
        return core.query_resource(context, models.DestinationCidr,route_filters,[])


    def _create_route_entry_destination_cidrs(self,context,route_entry_id,routes):
        destination = None
        print "MaXiao Print cidr destination :"+str(destination)
        try:
            with context.session.begin(subtransactions=True):
                for rt in routes:
                    destination=self.filter_to_str(common_utils.AuthenticIPNetwork(rt['destination']))
                    print "MaXiao Print cidr destination :"+str(destination)
                    new_core_routerroute = core.create_resource(
                        context, models.DestinationCidr,
                        {'route_entry_id': route_entry_id,
                         'destination':destination})
        except db_exc.DBDuplicateEntry as e1:
            LOG.exception('Record destination_cidr already exists : '
                          'route_entry_id%(route_entry_id)s: '
                          'destination%(destination)s: '
                          '%(exception)s',
                          {'route_entry_id': route_entry_id,
                           'destination':destination,
                           'exception': e1})

            raise t_exceptions.RouteEntryDestinationCidrsCreateException()
        except Exception as e2:
            LOG.exception('Failed to create destination_cidr : '
                          'route_entry_id %(route_entry_id)s: '
                          'destination%(destination)s: '
                          '%(exception)s',
                          {'route_entry_id': route_entry_id,
                           'destination':destination,
                           'exception': e2})
            raise t_exceptions.RouteEntryDestinationCidrsCreateException()

    def _update_route_entry_destination_cidrs(self, context, route_entry_id, route_entry):

        def _combine(ht):
            return "{}".format(ht['destination'])

        try:
            with context.session.begin(subtransactions=True):

                old_route_list = self._get_destination_cidrs_by_route_entry_id(context, route_entry_id)

                new_route_set = set([_combine(route)
                                     for route in route_entry['destination_cidr_list']])

                old_route_set = set([_combine(route)
                                     for route in old_route_list])

                new_routes = []
                for route_str in old_route_set - new_route_set:
                    for route in old_route_list:
                        if _combine(route) == route_str:
                            destination=self.filter_to_str(common_utils.AuthenticIPNetwork(route_str.partition("_")[0]))
                            route_filters = [{'key': 'route_entry_id','comparator':'eq','value':route_entry_id},
                                              {'key': 'destination','comparator':'eq','value':destination}]
                            core.delete_resources(context, models.DestinationCidr, route_filters)
                for route_str in new_route_set - old_route_set:
                    destination=self.filter_to_str(common_utils.AuthenticIPNetwork(route_str.partition("_")[0]))
                    new_core_routerroute = core.create_resource(
                        context, models.DestinationCidr,
                        {'route_entry_id': route_entry_id,
                          'destination':destination})

                for route_str in new_route_set:
                    new_routes.append(
                        {'destination': route_str})
                del route_entry["destination_cidr_list"]
                return new_routes
        except Exception as e:
            LOG.exception('Failed to update destination_cidr: '
                          'route_entry_id %(route_entry_id)s: '
                          '%(exception)s',
                          {'route_entry_id': route_entry_id,
                           'exception': e})
            raise t_exceptions.RouteEntryDestinationCidrsUpdateException()


    @expose(generic=True, template='json')
    def post(self, **kw):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_CREATE):
            pecan.abort(401, _('Unauthorized to create route_entry'))
            return
        route_entry = request.context['request_data']['route_entry']

        src_router= route_entry.get('src_router', '').strip()
        nxt_router= route_entry.get('nxt_router', '').strip()
        project_id= route_entry.get('project_id', '').strip()
        destination_cidr_list= route_entry.get('destination_cidr_list',[])
        admin_state_up = route_entry.get('admin_state_up',True)
        status = route_entry.get('status',"DOWN")
        description = route_entry.get('description', '').strip()

        _uuid = uuidutils.generate_uuid()

        if src_router == nxt_router:
            return_object = m.RouteEntryRouterIDSame(src_router=src_router,nxt_router=nxt_router)
            return return_object.to_dict()

        try:
            with context.session.begin():
                new_route_entry = core.create_resource(
                    context, models.RouteEntry,
                    {'id': _uuid,
                     'src_router':src_router,
                     'nxt_router': nxt_router,
                     'project_id': project_id,
                     'admin_state_up':admin_state_up,
                     'status':status,
                     'description':description})
                if validators.is_attr_set(destination_cidr_list):
                    self._create_route_entry_destination_cidrs(context,_uuid,destination_cidr_list)
                new_route_entry= core.get_resource(context, models.RouteEntry, _uuid)
            return_object = m.SuccessMessage(result={'route_entry':new_route_entry})
            return return_object.to_dict()
        except db_exc.DBDuplicateEntry as e1:
            LOG.exception('Record route_entry already exists for '
                          'src_router %(src_router)s: '
                          'nxt_router%(nxt_router)s: '
                          '%(exception)s',
                          {'src_router': src_router,
                           'nxt_router':nxt_router,
                           'exception': e1})
            return_object = m.RouteEntryExists(src_router=src_router,nxt_router=nxt_router)
            return return_object.to_dict()
        except Exception as e2:
            LOG.exception('Failed to create route_entry: '
                          'src_router: %(src_router)s,'
                          'nxt_router %(nxt_router)s: '
                          '%(exception)s ',
                           {'src_router': src_router,
                            'nxt_router':nxt_router,
                           'exception': e2})
            return_object = m.FailureMessage()
            return return_object.to_dict()

    @expose(generic=True, template='json')
    def put(self, _id, **kw):
        context = t_context.extract_context_from_environ()
        route_entry = request.context['request_data']['route_entry']
        try:
            with context.session.begin():
                core.get_resource_object(context, models.RouteEntry, _id)

                if 'destination_cidr_list' in route_entry:
                    self._update_route_entry_destination_cidrs(context, _id, route_entry)

                route_entry_updated= core.update_resource(
                    context,models.RouteEntry, _id, route_entry)
                return_object = m.SuccessMessage(result={'route_entry':route_entry_updated})
                return return_object.to_dict()

        except t_exceptions.ResourceNotFound as e1:
            LOG.exception('Failed to update route_entry : '
                          'id%(id)s ,''%(exception)s ',
                           {'id':_id,
                            'exception': e1})
            return m.RouteEntryNotFound(id=_id).to_dict()
        except Exception as e2:
            LOG.exception('Failed to update route_entry: '
                          'id: %(id)s,'
                          '%(exception)s ',
                           {'id': _id,
                           'exception': e2})
            return_object = m.FailureMessage()
            return return_object.to_dict()

    @expose(generic=True, template='json')
    def get_one(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_SHOW):
            pecan.abort(401, _('Unauthorized to show route_entry'))
            return

        try:
            return_object = m.SuccessMessage(result={'route_entry':
                                    db_api.get_route_entry(context, _id)})
            return return_object.to_dict()

        except t_exceptions.ResourceNotFound as e1:
            LOG.exception('Failed to show route_entry : '
                          'id%(id)s ,''%(exception)s ',
                           {'id':_id,
                            'exception': e1})
            return m.RouteEntryNotFound(id=_id).to_dict()
        except Exception as e2:
            LOG.exception('Failed to show route_entry: '
                          'id: %(id)s,'
                          '%(exception)s ',
                           {'id': _id,
                           'exception': e2})
            return_object = m.FailureMessage()
            return return_object.to_dict()


    @expose(generic=True, template='json')
    def get_all(self):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_LIST):
            pecan.abort(401, _('Unauthorized to list route_entry'))
            return

        try:
            return_object = m.SuccessMessage(result={'route_entrys':
                                    db_api.list_route_entrys(context)})
            return return_object.to_dict()
        except Exception as e:
            LOG.exception('Failed to list route_entrys: '
                          '%(exception)s ',
                           {'exception': e})
            return_object = m.FailureMessage()
            return return_object.to_dict()

    @expose(generic=True, template='json')
    def delete(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_DELETE):
            pecan.abort(401, _('Unauthorized to delete route_entry'))
            return

        try:
            with context.session.begin():
                core.delete_resource(context, models.RouteEntry, _id)
            return_object = m.SuccessMessage(result={})
            return return_object.to_dict()
        except t_exceptions.ResourceNotFound as e1:
            LOG.exception('Failed to delete route_entry : '
                          'id%(id)s ,''%(exception)s ',
                           {'id':_id,
                            'exception': e1})
            return m.RouteEntryNotFound(id=_id).to_dict()
        except Exception as e2:
            LOG.exception('Failed to delete route_entry: '
                          'id: %(id)s,'
                          '%(exception)s ',
                           {'id': _id,
                           'exception': e2})
            return_object = m.FailureMessage()
            return return_object.to_dict()
