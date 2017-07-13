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
from tricircle.common import return_message as m

from tricircle.common import utils

LOG = logging.getLogger(__name__)

class FirewallBypasssController(rest.RestController):

    @expose(generic=True, template='json')
    def post(self, **kw):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_CREATE):
            pecan.abort(401, _('Unauthorized to create firewall_bypass'))
            return

        firewall_bypass = request.context['request_data']['firewall_bypass']

        fabric= firewall_bypass.get('fabric', '').strip()
        core_router_id= firewall_bypass.get('core_router_id', '').strip()
        router_id= firewall_bypass.get('router_id', '').strip()
        project_id= firewall_bypass.get('project_id', '').strip()
        admin_state_up = firewall_bypass.get('admin_state_up',True)
        status = firewall_bypass.get('status',"DOWN")
        description = firewall_bypass.get('description', '').strip()

        _uuid = uuidutils.generate_uuid()

        try:
            with context.session.begin():
                core_router_object = core.get_resource_object(context, models.CoreRouter, core_router_id)
                new_firewall_bypass = core.create_resource(
                    context, models.FirewallBypass,
                    {'id': _uuid,
                     'fabric':fabric,
                     'core_router_id': core_router_id,
                     'router_id': router_id,
                     'project_id': project_id,
                     'admin_state_up':admin_state_up,
                     'status':status,
                     'description':description})
            return_object = m.SuccessMessage(result={'firewall_bypass':new_firewall_bypass})
            return return_object.to_dict()

        except t_exceptions.ResourceNotFound as e:
            LOG.exception('Failed to add firewall_bypass: '
                          'core_router_id %(core_router_id)s not exists,'
                          '%(exception)s ',
                           {'core_router_id':core_router_id,
                            'exception': e})
            return m.CoreRouterNotFound(core_router_id=core_router_id).to_dict()
        except db_exc.DBDuplicateEntry as e1:
            LOG.exception('Record firewall_bypass already exists for '
                          'router_id %(router_id)s: '
                          'core_router_id %(core_router_id)s: '
                          '%(exception)s',
                          {'router_id': router_id,
                           'core_router_id':core_router_id,
                           'exception': e1})
            return_object = m.FirewallBypassExists(router_id=router_id,core_router_id=core_router_id)
            return return_object.to_dict()
        except Exception as e2:
            LOG.info('Failed to create firewall_bypass: '
                          'router_id: %(router_id)s,'
                          'core_router_id %(core_router_id)s: '
                          '%(exception)s ',
                           {'router_id': router_id,
                            'core_router_id':core_router_id,
                           'exception': e2})
            return_object = m.FailureMessage()
            return return_object.to_dict()

    @expose(generic=True, template='json')
    def put(self, _id, **kw):
        context = t_context.extract_context_from_environ()
        firewall_bypass = request.context['request_data']['firewall_bypass']
        try:
            with context.session.begin():
                core.get_resource_object(context, models.FirewallBypass, _id)
                firewall_bypass_updated= core.update_resource(
                    context,models.FirewallBypass, _id, firewall_bypass)
                return_object = m.SuccessMessage(result={'firewall_bypass':firewall_bypass_updated})
                return return_object.to_dict()

        except t_exceptions.ResourceNotFound as e1:
            LOG.exception('Failed to update firewall_bypass : '
                          'id%(id)s ,''%(exception)s ',
                           {'id':_id,
                            'exception': e1})
            return m.FirewallBypassNotFound(id=_id).to_dict()
        except Exception as e2:
            LOG.exception('Failed to update firewall_bypass: '
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
            pecan.abort(401, _('Unauthorized to show firewall_bypass'))
            return

        try:
            return_object = m.SuccessMessage(result={'firewall_bypass':
                                    db_api.get_firewall_bypass(context, _id)})
            return return_object.to_dict()

        except t_exceptions.ResourceNotFound as e1:
            LOG.exception('Failed to show firewall_bypass : '
                          'id%(id)s ,''%(exception)s ',
                           {'id':_id,
                            'exception': e1})
            return m.FirewallBypassNotFound(id=_id).to_dict()
        except Exception as e2:
            LOG.exception('Failed to show firewall_bypass: '
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
            pecan.abort(401, _('Unauthorized to list firewall_bypass'))
            return

        try:
            return_object = m.SuccessMessage(result={'firewall_bypasss':
                                    db_api.list_firewall_bypasss(context)})
            return return_object.to_dict()
        except Exception as e:
            LOG.exception('Failed to list firewall_bypasss: '
                          '%(exception)s ',
                           {'exception': e})
            return_object = m.FailureMessage()
            return return_object.to_dict()

    @expose(generic=True, template='json')
    def delete(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_DELETE):
            pecan.abort(401, _('Unauthorized to delete firewall_bypass'))
            return

        try:
            with context.session.begin():
                core.delete_resource(context, models.FirewallBypass, _id)
            return_object = m.SuccessMessage(result={})
            return return_object.to_dict()
        except t_exceptions.ResourceNotFound as e1:
            LOG.exception('Failed to delete firewall_bypass : '
                          'id%(id)s ,''%(exception)s ',
                           {'id':_id,
                            'exception': e1})
            return m.FirewallBypassNotFound(id=_id).to_dict()
        except Exception as e2:
            LOG.exception('Failed to delete firewall_bypass: '
                          'id: %(id)s,'
                          '%(exception)s ',
                           {'id': _id,
                           'exception': e2})
            return_object = m.FailureMessage()
            return return_object.to_dict()
