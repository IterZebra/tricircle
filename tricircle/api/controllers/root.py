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
from pecan import request
from pecan import rest
from tricircle.api.controllers import region
from tricircle.api.controllers import dc
from tricircle.api.controllers import fabric
from tricircle.api.controllers import job
from tricircle.api.controllers import tricircle_resource
from tricircle.api.controllers import pod
from tricircle.api.controllers import core_router
from tricircle.api.controllers import dci
from tricircle.api.controllers import dynamic_peering_connection
from tricircle.api.controllers import firewall_gateway 
from tricircle.api.controllers import firewall_bypass 
from tricircle.api.controllers import route_entry 
from tricircle.api.controllers import routing
import tricircle.common.context as t_context
import webob.exc

def expose(*args, **kwargs):
    kwargs.setdefault('content_type', 'application/json')
    kwargs.setdefault('template', 'json')
    return pecan.expose(*args, **kwargs)


def when(index, *args, **kwargs):
    kwargs.setdefault('content_type', 'application/json')
    kwargs.setdefault('template', 'json')
    return index.when(*args, **kwargs)


class RootController(object):

    @expose()
    def _lookup(self, version, *remainder):
        if version == 'svpc':
            return V1Controller(), remainder
        else:
            msg = "URL not found "
            raise webob.exc.HTTPBadRequest(msg)       
 
    @pecan.expose(generic=True, template='json')
    def index(self):
        return {
            "versions": [
                {
                    "status": "CURRENT",
                    "links": [
                        {
                            "rel": "self",
                            "href": pecan.request.application_url + "/v1.0/"
                            }
                        ],
                    "id": "v1.0",
                    "updated": "2015-09-09"
                    }
                ]
            }

    @index.when(method='POST')
    @index.when(method='PUT')
    @index.when(method='DELETE')
    @index.when(method='HEAD')
    @index.when(method='PATCH')
    def not_supported(self):
        pecan.abort(405)


class V1Controller(rest.RestController):

    def __init__(self):

        self.sub_controllers = {
            "regions": region.RegionsController(),
            "dcs": dc.DCsController(),
            "fabrics": fabric.FabricsController(),
            "tricircle_resources": tricircle_resource.TricircleResourcesController(),
            "core_routers": core_router.CoreRoutersController(),
            "dcis": dci.DCIsController(),
            "dynamic_peering_connections": dynamic_peering_connection.DynamicPeeringConnectionsController(),
            "firewall_gateways": firewall_gateway.FirewallGatewaysController(),
            "firewall_bypasss": firewall_bypass.FirewallBypasssController(),
            "route_entries": route_entry.RouteEntrysController(),
            "pods": pod.PodsController(),
            "routings": routing.RoutingController(),
            "jobs": job.AsyncJobController()
        }

        for name, ctrl in self.sub_controllers.items():
            setattr(self, name, ctrl)

    @pecan.expose()
    def _lookup(self, resource , *remainder):
        if resource== 'regions':
            request.context['resource'] = "region" 
            return self.regions,remainder
        if resource== 'dcs':
            request.context['resource'] = "dc" 
            return self.dcs,remainder
        if resource== 'fabrics':
            request.context['resource'] = "fabric" 
            return self.fabrics,remainder
        if resource== 'tricircle_resources':
            request.context['resource'] = "tricircle_resource" 
            return self.tricircle_resources,remainder
        if resource== 'routers':
            request.context['resource'] = "core_router" 
            return self.core_routers,remainder
        if resource== 'core_routers':
            request.context['resource'] = "core_router" 
            return self.core_routers,remainder
        if resource== 'dynamic_peering_connections':
            request.context['resource'] = "dynamic_peering_connection" 
            return self.dynamic_peering_connections,remainder
        if resource== 'firewall_gateways':
            request.context['resource'] = "firewall_gateway" 
            return self.firewall_gateways,remainder
        if resource== 'firewall_bypasss':
            request.context['resource'] = "firewall_bypass" 
            return self.firewall_bypasss,remainder
        if resource== 'route_entry':
            request.context['resource'] = "route_entry" 
            return self.route_entries,remainder
        if resource== 'pods':
            request.context['resource'] = "pod" 
            return self.pods,remainder
        if resource== 'dcis':
            request.context['resource'] = "dci" 
            return self.dcis,remainder
        else:
            msg = "URL not found "
            raise webob.exc.HTTPBadRequest(msg)       

    @pecan.expose(generic=True, template='json')
    def index(self):
        return {
            "version": "1.0",
            "links": [
                {"rel": "self",
                 "href": pecan.request.application_url + "/v1.0"}
            ] + [
                {"rel": name,
                 "href": pecan.request.application_url + "/v1.0/" + name}
                for name in sorted(self.sub_controllers)
            ]
        }

    @index.when(method='POST')
    @index.when(method='PUT')
    @index.when(method='DELETE')
    @index.when(method='HEAD')
    @index.when(method='PATCH')
    def not_supported(self):
        pecan.abort(405)


def _extract_context_from_environ(environ):
    context_paras = {'auth_token': 'HTTP_X_AUTH_TOKEN',
                     'user': 'HTTP_X_USER_ID',
                     'tenant': 'HTTP_X_TENANT_ID',
                     'user_name': 'HTTP_X_USER_NAME',
                     'tenant_name': 'HTTP_X_PROJECT_NAME',
                     'domain': 'HTTP_X_DOMAIN_ID',
                     'user_domain': 'HTTP_X_USER_DOMAIN_ID',
                     'project_domain': 'HTTP_X_PROJECT_DOMAIN_ID',
                     'request_id': 'openstack.request_id'}
    for key in context_paras:
        context_paras[key] = environ.get(context_paras[key])
    role = environ.get('HTTP_X_ROLE')
    # TODO(zhiyuan): replace with policy check
    context_paras['is_admin'] = role == 'admin'
    return t_context.Context(**context_paras)


def _get_environment():
    return request.environ
