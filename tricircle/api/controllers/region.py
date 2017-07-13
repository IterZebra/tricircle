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

class RegionsController(rest.RestController):

    def __init__(self):
        self.resource = "regions"
        pass

    @expose(generic=True, template='json')
    def post(self, **kw):
        context = t_context.extract_context_from_environ()

        if 'region' not in kw:
            pecan.abort(400, _('Request body region not found'))
            return
        print 'MaXiao kw '+str(request.context['request_data'])
        region = request.context['request_data']['region']
        region_name = region.get('region_name', '').strip()
        _uuid = uuidutils.generate_uuid()
        try:
            with context.session.begin():
                new_region = core.create_resource(
                    context, models.Region,
                    {'id': _uuid,
                     'region_name': region_name})
        except db_exc.DBDuplicateEntry as e1:
            LOG.exception('Record already exists on %(region_name)s: '
                          '%(exception)s',
                          {'region_name': region_name,
                           'exception': e1})
            return Response(_('Record already exists'), 409)
        except Exception as e2:
            LOG.exception('Failed to create region: %(region_name)s,'
                          '%(exception)s ',
                          {'region_name': region_name,
                           'exception': e2})
            return Response(_('Failed to create region'), 500)

        return {'region': new_region}

    @expose(generic=True, template='json')
    def get_one(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_SHOW):
            pecan.abort(401, _('Unauthorized to show regions'))
            return

        try:
            return {'region': db_api.get_region(context, _id)}
        except t_exceptions.ResourceNotFound:
            pecan.abort(404, _('Region not found'))
            return

    @expose(generic=True, template='json')
    def get_all(self):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_LIST):
            pecan.abort(401, _('Unauthorized to list regions'))
            return

        try:
            return {'regions': db_api.list_regions(context)}
        except Exception as e:
            LOG.exception('Failed to list all regions: %(exception)s ',
                          {'exception': e})

            pecan.abort(500, _('Failed to list regions'))
            return

    @expose(generic=True, template='json')
    def delete(self, _id):
        context = t_context.extract_context_from_environ()

        if not policy.enforce(context, policy.ADMIN_API_PODS_DELETE):
            pecan.abort(401, _('Unauthorized to delete regions'))
            return

        try:
            with context.session.begin():
                print "MaXiao 111  delete region has dcs "
                region_object = core.get_resource_object(context, models.Region, _id)
                print "MaXiao delete region has dcs :"+str(region_result)
                if len(region_object.dcs)>0:
                    raise t_exceptions.InUse("Specified region has dc(s)")
                core.delete_resource(context, models.Region, _id)
                pecan.response.status = 200
                return {}
        except t_exceptions.InUse:
            return Response(_('Specified region has dcs'), 400)
        except t_exceptions.ResourceNotFound:
            return Response(_('Region not found'), 404)
        except Exception as e:
            LOG.exception('Failed to delete region: %(region_id)s,'
                          '%(exception)s',
                          {'region_id': _id,
                           'exception': e})

            return Response(_('Failed to delete region'), 500)
