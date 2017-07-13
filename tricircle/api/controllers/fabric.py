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

import pecan
from pecan import expose
from pecan import Response
from pecan import rest
from pecan import request
import oslo_db.exception as db_exc
from oslo_log import log as logging
from oslo_utils import uuidutils

import tricircle.common.context as t_context
import tricircle.common.exceptions as t_exceptions
from tricircle.common.i18n import _
from tricircle.common import policy

from tricircle.db import api as db_api
from tricircle.db import core
from tricircle.db import models

LOG = logging.getLogger(__name__)

class FabricsController(rest.RestController):

    def __init__(self):
        self.resource = "fabrics"
        pass

    @expose(generic=True, template='json')
    def post(self, **kw):
        context = t_context.extract_context_from_environ()

        if 'fabric' not in kw:
            pecan.abort(400, _('Request body fabric not found'))
            return
        print 'MaXiao kw '+str(request.context['request_data'])
        fabric = request.context['request_data']['fabric']
        fabric_name = fabric.get('fabric_name', '').strip()
        dc_id= fabric.get('dc_id', '').strip()
        _uuid = uuidutils.generate_uuid()
        try:
            with context.session.begin():
                core.get_resource(context, models.DC, dc_id)
                new_fabric = core.create_resource(
                    context, models.Fabric,
                    {'id': _uuid,
                     'fabric_name': fabric_name,
                     'dc_id':dc_id})
        except t_exceptions.ResourceNotFound:
            return Response(_('Specified dc not found'), 404)
        except db_exc.DBDuplicateEntry as e1:
            LOG.exception('Record already exists on %(fabric_name)s,'
                          'dc_id: %(dc_id)s,'
                          '%(exception)s',
                          {'fabric_name': fabric_name,
                           'dc_id':dc_id,
                           'exception': e1})
            return Response(_('Record already exists'), 409)
        except Exception as e2:
            LOG.exception('Failed to create fabric: %(fabric_name)s,'
                          'dc_id: %(dc_id)s,'
                          '%(exception)s ',
                          {'fabric_name': fabric_name,
                           'dc_id':dc_id,
                           'exception': e2})
            return Response(_('Failed to create fabric'), 500)

        return {'fabric': new_fabric}

    @expose(generic=True, template='json')
    def get_one(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_SHOW):
            pecan.abort(401, _('Unauthorized to show fabrics'))
            return

        try:
            return {'fabric': db_api.get_fabric(context, _id)}
        except t_exceptions.ResourceNotFound:
            pecan.abort(404, _('Fabric not found'))
            return

    @expose(generic=True, template='json')
    def get_all(self):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_LIST):
            pecan.abort(401, _('Unauthorized to list fabrics'))
            return

        try:
            return {'fabrics': db_api.list_fabrics(context)}
        except Exception as e:
            LOG.exception('Failed to list all fabrics: %(exception)s ',
                          {'exception': e})

            pecan.abort(500, _('Failed to list fabrics'))
            return

    @expose(generic=True, template='json')
    def delete(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_DELETE):
            pecan.abort(401, _('Unauthorized to delete fabrics'))
            return

        try:
            with context.session.begin():
                core.delete_resource(context, models.Fabric, _id)
                pecan.response.status = 200
                return {}
        except t_exceptions.ResourceNotFound:
            return Response(_('Fabric not found'), 404)
        except Exception as e:
            LOG.exception('Failed to delete fabric: %(fabric_id)s,'
                          '%(exception)s',
                          {'fabric_id': _id,
                           'exception': e})

            return Response(_('Failed to delete fabric'), 500)
