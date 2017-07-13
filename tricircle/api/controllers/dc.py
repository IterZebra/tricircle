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

class DCsController(rest.RestController):

    def __init__(self):
        self.resource = "dcs"
        pass

    @expose(generic=True, template='json')
    def post(self, **kw):
        context = t_context.extract_context_from_environ()

        if 'dc' not in kw:
            pecan.abort(400, _('Request body dc not found'))
            return
        print 'MaXiao kw '+str(request.context['request_data'])
        dc = request.context['request_data']['dc']
        dc_name = dc.get('dc_name', '').strip()
        region_id= dc.get('region_id', '').strip()
        _uuid = uuidutils.generate_uuid()
        try:
            with context.session.begin():
                core.get_resource(context, models.Region, region_id)
                new_dc = core.create_resource(
                    context, models.DC,
                    {'id': _uuid,
                     'dc_name': dc_name,
                     'region_id':region_id})
        except t_exceptions.ResourceNotFound:
            return Response(_('Specified region not found'), 404)
        except db_exc.DBDuplicateEntry as e1:
            LOG.exception('Record already exists on %(dc_name)s,'
                          'region_id: %(region_id)s,'
                          '%(exception)s',
                          {'dc_name': dc_name,
                           'region_id':region_id,
                           'exception': e1})
            return Response(_('Record already exists'), 409)
        except Exception as e2:
            LOG.exception('Failed to create dc: %(dc_name)s,'
                          'region_id: %(region_id)s,'
                          '%(exception)s ',
                          {'dc_name': dc_name,
                           'region_id':region_id,
                           'exception': e2})
            return Response(_('Failed to create dc'), 500)

        return {'dc': new_dc}

    @expose(generic=True, template='json')
    def get_one(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_SHOW):
            pecan.abort(401, _('Unauthorized to show dcs'))
            return

        try:
            return {'dc': db_api.get_dc(context, _id)}
        except t_exceptions.ResourceNotFound:
            pecan.abort(404, _('DC not found'))
            return

    @expose(generic=True, template='json')
    def get_all(self):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_LIST):
            pecan.abort(401, _('Unauthorized to list dcs'))
            return

        try:
            return {'dcs': db_api.list_dcs(context)}
        except Exception as e:
            LOG.exception('Failed to list all dcs: %(exception)s ',
                          {'exception': e})

            pecan.abort(500, _('Failed to list dcs'))
            return

    @expose(generic=True, template='json')
    def delete(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_DELETE):
            pecan.abort(401, _('Unauthorized to delete dcs'))
            return

        try:
            with context.session.begin():
                region_object = core.get_resource_object(context, models.DC, _id)
                if len(region_object.fabrics) >0:
                    raise t_exceptions.InUse("Specified dc has fabric(s)")
                if len(region_object.core_routers) >0:
                    raise t_exceptions.InUse("Specified dc has core_router(s)")
                core.delete_resource(context, models.DC, _id)
                pecan.response.status = 200
                return {}
        except t_exceptions.InUse:
            return Response(_('Specified region has dcs/core_routers'), 400)
        except t_exceptions.ResourceNotFound:
            return Response(_('DC not found'), 404)
        except Exception as e:
            LOG.exception('Failed to delete dc: %(dc_id)s,'
                          '%(exception)s',
                          {'dc_id': _id,
                           'exception': e})

            return Response(_('Failed to delete dc'), 500)
