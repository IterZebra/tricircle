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

LOG = logging.getLogger(__name__)

class DynamicPeeringConnectionsController(rest.RestController):

    @expose(generic=True, template='json')
    def post(self, **kw):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_CREATE):
            pecan.abort(401, _('Unauthorized to create dynamic peering connection'))
            return

        if 'dynamic_peering_connection' not in kw:
            pecan.abort(400, _('Request body dynamic_peering_connection not found'))
            return
        print 'MaXiao kw '+str(request.context['request_data'])
        dynamic_peering_connection = request.context['request_data']['dynamic_peering_connection']

        dynamic_peering_connection_name = dynamic_peering_connection.get('dynamic_peering_connection_name', '').strip()
        project_id= dynamic_peering_connection.get('project_id', '').strip()
        local_router_id= dynamic_peering_connection.get('local_router_id', '').strip()
        peering_router_id= dynamic_peering_connection.get('peering_router_id', '').strip()
        if local_router_id == peering_router_id:
            pecan.abort(400, _('Request body local_router_id is same with peering_router_id'))
            return
         
        description = dynamic_peering_connection.get('description', '').strip()
        admin_state_up = dynamic_peering_connection.get('admin_state_up',True)
        status = dynamic_peering_connection.get('status',"DOWN")

        _uuid = uuidutils.generate_uuid()

        try:
            with context.session.begin():
                core.get_resource(context, models.CoreRouter, local_router_id)
                core.get_resource(context, models.CoreRouter, peering_router_id)
                new_dynamic_peering_connection = core.create_resource(
                    context, models.DynamicPeeringConnection,
                    {'dynamic_peering_connection_id': _uuid,
                     'dynamic_peering_connection_name':dynamic_peering_connection_name,
                     'project_id': project_id,
                     'local_router_id': local_router_id,
                     'peering_router_id':peering_router_id,
                     'admin_state_up':admin_state_up,
                     'status':status,
                    'description':description})
        except t_exceptions.ResourceNotFound as e0:
            LOG.exception('Record router not exists on'
                          'local_router_id %(local_router_id)s: '
                          'peering_router_id %(peering_router_id)s: '
                          '%(exception)s',
                          {'local_router_id': local_router_id,
                           'peering_router_id': peering_router_id,
                           'exception': e0})
            pecan.abort(404, _('Failed to create dynamic peering connection,core router not found'))
            return
    
        except db_exc.DBDuplicateEntry as e1:
            LOG.exception('Record already exists on'
                          'local_router_id %(local_router_id)s: '
                          'peering_router_id %(peering_router_id)s: '
                          '%(exception)s',
                          {'local_router_id': local_router_id,
                           'peering_router_id': peering_router_id,
                           'exception': e1})
            return Response(_('Record already exists'), 409)
        except Exception as e2:
            LOG.exception('Failed to create dynamic_peering_connection :'
                          'local_router_id: %(local_router_id)s,'
                          'peering_router_id: %(peering_router_id)s,'
                          '%(exception)s ',
                          {'local_router_id': local_router_id,
                           'peering_router_id': peering_router_id,
                           'exception': e2})
            return Response(_('Failed to create dynamic_peering_connection'), 500)

        return {'dynamic_peering_connection': new_dynamic_peering_connection}

    @expose(generic=True, template='json')
    def put(self, _id, **kw):
        context = t_context.extract_context_from_environ()

        print 'MaXiao put '+str(request.context['request_data'])
        dynamic_peering_connection = request.context['request_data']['dynamic_peering_connection']
        try:
            with context.session.begin():
                core.get_resource(context, models.DynamicPeeringConnection, _id)
        except t_exceptions.ResourceNotFound:
            pecan.abort(404, _('Core Router not found'))
            return
        try:
           connection_updated= db_api.update_dynamic_peering_connection(
                    context, _id, dynamic_peering_connection)
           return {'dynamic_peering_connection': connection_updated}
        except t_exceptions.ResourceNotFound:
            pecan.abort(404, _('Dynamic Peering Connection not found'))
            return
        except Exception as e:
            LOG.exception('Failed to update dynamic peering connection : '
                          '%(exception)s ', {'exception': e})
            return utils.format_api_error(
                500, _('Failed to update dynamic peering connection '))

    @expose(generic=True, template='json')
    def get_one(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_SHOW):
            pecan.abort(401, _('Unauthorized to show core routers'))
            return

        try:
            return {'dynamic_peering_connection': db_api.get_dynamic_peering_connection(context, _id)}
        except t_exceptions.ResourceNotFound:
            pecan.abort(404, _('Dynamic Peering Connection not found'))
            return

    @expose(generic=True, template='json')
    def get_all(self):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_LIST):
            pecan.abort(401, _('Unauthorized to list dynamic peering connection'))
            return

        try:
            return {'dynamic_peering_connections': db_api.list_dynamic_peering_connections(context)}
        except Exception as e:
            LOG.exception('Failed to list all dynamic_peering_connections: %(exception)s ',
                          {'exception': e})

            pecan.abort(500, _('Failed to list dynamic_peering_connections'))
            return

    @expose(generic=True, template='json')
    def delete(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_DELETE):
            pecan.abort(401, _('Unauthorized to delete dynamic_peering_connections'))
            return

        try:
            with context.session.begin():
                core.delete_resource(context, models.DynamicPeeringConnection, _id)
                pecan.response.status = 200
                return {}
        except t_exceptions.ResourceNotFound:
            return Response(_('Dynamic Peering Connection not found'), 404)
        except Exception as e:
            LOG.exception('Failed to delete dynamic_peering_connection: %(dynamic_peering_connection_id)s,'
                          '%(exception)s',
                          {'dynamic_peering_connection_id': _id,
                           'exception': e})

            return Response(_('Failed to delete dynamic_peering_connection'), 500)


