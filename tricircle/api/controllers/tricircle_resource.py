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

class TricircleResourcesController(rest.RestController):

    @expose(generic=True, template='json')
    def post(self, **kw):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_CREATE):
            pecan.abort(401, _('Unauthorized to create tricircle resource'))
            return

        if 'tricircle_resource' not in kw:
            pecan.abort(400, _('Request body tricircle_resource not found'))
            return
        tricircle_resource = request.context['request_data']['tricircle_resource']

        tricircle_resource_id= tricircle_resource.get('id', '').strip()
        tricircle_resource_name = tricircle_resource.get('name', '').strip()
        region_name= tricircle_resource.get('region_name', '').strip()
        project_id= tricircle_resource.get('project_id', '').strip()
        resource_type= tricircle_resource.get('resource_type', '').strip()
        admin_state_up = tricircle_resource.get('admin_state_up',True)
        status = tricircle_resource.get('status',"DOWN")


        try:
            with context.session.begin():
                new_tricircle_resource= core.create_resource(
                    context, models.TricircleResource,
                    {'id': tricircle_resource_id,
                     'name':tricircle_resource_name,
                     'region_name':region_name,
                     'resource_type':resource_type,
                     'project_id': project_id,
                     'admin_state_up':admin_state_up,
                     'status':status})
    
        except db_exc.DBDuplicateEntry as e1:
            LOG.exception('Record already exists on'
                          'tricircle_resource_id%(tricircle_resource_id)s: '
                          '%(exception)s',
                          {'tricircle_resource_id':tricircle_resource_id,
                           'exception': e1})
            return Response(_('Record already exists'), 409)
        except Exception as e2:
            LOG.exception('Failed to create tricircle_resource :'
                          'tricircle_resource_id: %(tricircle_resource_id)s,'
                          '%(exception)s ',
                          {'tricircle_resource_id': tricircle_resource_id,
                           'exception': e2})
            return Response(_('Failed to create tricircle_resource'), 500)

        return {'tricircle_resource': new_tricircle_resource}

    @expose(generic=True, template='json')
    def put(self, _id, **kw):
        context = t_context.extract_context_from_environ()

        tricircle_resource = request.context['request_data']['tricircle_resource']
        try:
            with context.session.begin():
                core.get_resource(context, models.TricircleResource, _id)
        except t_exceptions.ResourceNotFound:
            pecan.abort(404, _('Tricircle resource not found'))
            return
        try:
           tricircle_resource_updated= db_api.update_tricircle_resource(
                    context, _id, tricircle_resource)
           return {'tricircle_resource': tricircle_resource_updated}
        except t_exceptions.ResourceNotFound:
            pecan.abort(404, _('Tricircle resource not found'))
            return
        except Exception as e:
            LOG.exception('Failed to update tricircle resource : '
                          '%(exception)s ', {'exception': e})
            return utils.format_api_error(
                500, _('Failed to update tricircle resource '))

    @expose(generic=True, template='json')
    def get_one(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_SHOW):
            pecan.abort(401, _('Unauthorized to show tricircle resource'))
            return

        try:
            return {'tricircle_resource': db_api.get_tricircle_resource(context, _id)}
        except t_exceptions.ResourceNotFound:
            pecan.abort(404, _('Tricircle resource not found'))
            return

    @expose(generic=True, template='json')
    def get_all(self):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_LIST):
            pecan.abort(401, _('Unauthorized to list tricircle_resources'))
            return

        try:
            return {'tricircle_resources': db_api.list_tricircle_resources(context)}
        except Exception as e:
            LOG.exception('Failed to list all tricircle_resources: %(exception)s ',
                          {'exception': e})

            pecan.abort(500, _('Failed to list tricircle_resources'))
            return

    @expose(generic=True, template='json')
    def delete(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_DELETE):
            pecan.abort(401, _('Unauthorized to delete tricircle_resources'))
            return

        try:
            with context.session.begin():
                core.delete_resource(context, models.TricircleResource, _id)
                pecan.response.status = 200
                return {}
        except t_exceptions.ResourceNotFound:
            return Response(_('Firewall gateway not found'), 404)
        except Exception as e:
            LOG.exception('Failed to delete tricircle_resource: %(tricircle_resource_id)s,'
                          '%(exception)s',
                          {'tricircle_resource_id': _id,
                           'exception': e})

            return Response(_('Failed to delete tricircle_resource'), 500)
