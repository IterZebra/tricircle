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

class DCIsController(rest.RestController):

    @expose(generic=True, template='json')
    def post(self, **kw):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_CREATE):
            pecan.abort(401, _('Unauthorized to create dci'))
            return
        dci = request.context['request_data']['dci']
        fabric= dci.get('fabric', '').strip()
        router_id= dci.get('router_id', '').strip()
        dci_peering_id= dci.get('dci_peering_id', '').strip()
        project_id= dci.get('project_id', '').strip()
        dci_type= dci.get('type', '').strip()
        name = dci.get('name', '').strip()
        admin_state_up = dci.get('admin_state_up',True)
        status = dci.get('status',"DOWN")
        description = dci.get('description', '').strip()

        _uuid = uuidutils.generate_uuid()

        if router_id == dci_peering_id:
            return_object = m.DCIRouterIDSame(router_id=router_id,dci_peering_id=dci_peering_id,type=dci_type)
            return return_object.to_dict()

        try:
            with context.session.begin():
                new_dci = core.create_resource(
                    context, models.DCI,
                    {'id': _uuid,
                     'fabric':fabric,
                     'router_id': router_id,
                     'dci_peering_id': dci_peering_id,
                     'type':dci_type,
                     'name':name,
                     'project_id':project_id,
                     'admin_state_up':admin_state_up,
                     'status':status,
                     'description':description})
  
            return_object = m.SuccessMessage(result={'dci': new_dci})
            return return_object.to_dict()
 
        except db_exc.DBDuplicateEntry as e1:
            LOG.exception('Record dci already exists for '
                          'router_id %(router_id)s, '
                          'dci_peering_id %(dci_peering_id)s, '
                          'type %(type)s, '
                          'fabric %(fabric)s, '
                          '%(exception)s',
                          {'router_id': router_id,
                           'dci_peering_id': dci_peering_id,
                           'type': dci_type,
                           'fabric': fabric,
                           'exception': e1})

            return_object = m.DCIExists(router_id=router_id,dci_peering_id=dci_peering_id,type=dci_type)
            return return_object.to_dict()
        except Exception as e2:
            LOG.exception('Failed to create dci :'
                          'router_id: %(router_id)s,'
                          'dci_peering_id: %(dci_peering_id)s,'
                          'type %(type)s, '
                          'fabric %(fabric)s, '
                          '%(exception)s ',
                          {'router_id': router_id,
                           'dci_peering_id': dci_peering_id,
                           'type': dci_type,
                           'fabric': fabric,
                           'exception': e2})
            return_object = m.FailureMessage()
            return return_object.to_dict()

    @expose(generic=True, template='json')
    def put(self, _id, **kw):
        context = t_context.extract_context_from_environ()
        dci = request.context['request_data']['dci']
        try:
            with context.session.begin():
                core.get_resource_object(context, models.DCI, _id)
                connection_updated= core.update_resource(
                    context,models.DCI, _id, dci)
                return_object = m.SuccessMessage(result={'dci': connection_updated})
                return return_object.to_dict()
        except t_exceptions.ResourceNotFound as e:
            LOG.exception('Failed to update dci: '
                          'dci_id %(dci_id)s ,'
                          '%(exception)s ',
                           {'dci_id':_id,
                            'exception': e})
            return m.DCINotFound(dci_id=_id).to_dict()
        except Exception as e:
            LOG.exception('Failed to update dci: '
                          '%(exception)s ', {'exception': e})
            return_object = m.FailureMessage()
            return return_object.to_dict()

    @expose(generic=True, template='json')
    def get_one(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_SHOW):
            pecan.abort(401, _('Unauthorized to show dci'))
            return

        try:
            dci = db_api.get_dci(context, _id)
            return_object = m.SuccessMessage(result={'dci': dci})
            return return_object.to_dict()
        except t_exceptions.ResourceNotFound as e:
            LOG.exception('Failed to get dci: '
                          'dci_id %(dci_id)s ,'
                          '%(exception)s ',
                           {'dci_id':_id,
                           'exception': e})
            return m.DCINotFound(dci_id=_id).to_dict()
        except Exception as e:
            LOG.exception('Failed to get dci: %(dci_id)s,'
                          '%(exception)s',
                          {'dci_id': _id,
                           'exception': e})
            return_object = m.FailureMessage()
            return return_object.to_dict()

    @expose(generic=True, template='json')
    def get_all(self):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_LIST):
            pecan.abort(401, _('Unauthorized to list dcis'))
            return

        try:
            dcis = db_api.list_dcis(context)
            return_object = m.SuccessMessage(result={'dcis':dcis})
            return return_object.to_dict()
        except Exception as e:
            LOG.exception('Failed to list all dcis: '
                          '%(exception)s ', {'exception': e})
            return_object = m.FailureMessage()
            return return_object.to_dict()

    @expose(generic=True, template='json')
    def delete(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_DELETE):
            pecan.abort(401, _('Unauthorized to delete dcis'))
            return

        try:
            with context.session.begin():
                core.delete_resource(context, models.DCI, _id)
            return_object = m.SuccessMessage(result={})
            return return_object.to_dict()
        except t_exceptions.ResourceNotFound as e:
            LOG.exception('Failed to delete dci: '
                          'dci_id %(dci_id)s ,'
                          '%(exception)s ',
                           {'dci_id':_id,
                           'exception': e})
            return m.DCINotFound(dci_id=_id).to_dict()
        except Exception as e:
            LOG.exception('Failed to delete dci: %(dci_id)s,'
                          '%(exception)s',
                          {'dci_id': _id,
                           'exception': e})
            return_object = m.FailureMessage()
            return return_object.to_dict()
