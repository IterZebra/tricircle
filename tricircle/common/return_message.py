#!/usr/bin/python
# vim: set fileencoding=utf-8 :

#!/usr/bin/python
# -*- coding: UTF-8 -*-
# -*- coding: utf-8 -*-

# Copyright 2015 Huawei Technologies Co., Ltd.
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




"""
Tricircle base error message handling.
"""

import pecan
import six

from neutron_lib import exceptions
from oslo_log import log as logging

from tricircle.common.i18n import _


LOG = logging.getLogger(__name__)


class ReturnMessage(object):

    attributes=['status','message','content']

    status = 'fail'
    message = _("An unknown exception occurred.")
    content = {}
    code = 500
    def __init__(self, message=None, **kwargs):

        if message is not None:
            self.message = message
        self.kwargs = kwargs

        for k, v in self.kwargs.items():
            if isinstance(v, Exception):
                self.kwargs[k] = six.text_type(v)

        try:
            message = self.message % self.kwargs
            print "MaXiao message"+str(message)
        except Exception:

            # kwargs doesn't match a variable in the message
            # log the issue and the kwargs
            exc_info = _('ReturnMessage class %s in string '
                         'format operation') % type(self).__name__
            format_str = _('%(exception_info)s ; %(format_key)s : '
                           '%(format_value)s')
            for name, value in kwargs.items():
                exc_info = format_str % {
                    'exception_info': exc_info,
                    'format_key': name,
                    'format_value': six.text_type(value)}

            exc_info = _('%(message)s ; %(exception_info)s') % {
                'message': self.message, 'exception_info': exc_info}
            LOG.exception(exc_info)
            # no rerasie
            # exc_info = sys.exc_info()
            # if CONF.fatal_exception_format_errors:
            #    six.reraise(*exc_info)

            # at least get the core message out if something happened
            message = self.message

        self.message = message

    def to_dict(self):
        pecan.response.status = self.code
        d = {}
        for attr in self.__class__.attributes:
            d[attr] = getattr(self, attr)
        return d



class SuccessMessage(ReturnMessage):
    status = 'success'
    message = _("SUCCESS")
    content = {}
    code = 200 
    def __init__(self, message=None, **kwargs):
        self.content = kwargs.get("result")

class FailureMessage(ReturnMessage):
    status = 'fail'
    message = _("An unknown exception occurred.")
    content = {}
   
class ResourceNotFound(FailureMessage):
    message = _("Resource could not be found.")
    code = 404

class CoreRouterNotFound(ResourceNotFound):
    message = _("CoreRouter %(core_router_id)s could not be found.")
    
class CoreRouterInterfaceNotFound(ResourceNotFound):
    message = _("CoreRouterInterface core_router_id: %(core_router_id)s, fabric: %(fabric)s could not be found.")


class CoreRouterInUse(FailureMessage):
    message = _("CoreRouter has associated dependency resource(s).")
    code = 409

class CoreRouterForDCExists(FailureMessage):
    message = _("CoreRouter for dc: %(dc)s already exists.")
    code = 409

class CoreRouterInterfaceForFabricExists(FailureMessage):
    message = _("CoreRouterInterface for fabric: %(fabric)s already exists.")
    code = 409

class DCINotFound(ResourceNotFound):
    message = _("DCI %(dci_id)s could not be found.")

class DCIExists(FailureMessage):
    message = _("DCI for router_id : %(router_id)s, dci_peering_id : %(dci_peering_id)s, type : %(type)s already exists.")
    code = 409

class DCIRouterIDSame(FailureMessage):
    message = _("DCI for router_id : %(router_id)s same with dci_peering_id : %(dci_peering_id)s not valid.")
    code = 400 

class RouteEntryRouterIDSame(FailureMessage):
    message = _("RouteEntry for src_router : %(src_router)s same with nxt_router : %(nxt_router)s not valid.")
    code = 400 

class FirewallGatewayNotFound(ResourceNotFound):
    message = _("FirewallGateway %(id)s could not be found.")

class FirewallGatewayExists(FailureMessage):
    message = _("FirewallGateway for router_id : %(router_id)s, firewall_id : %(firewall_id)s already exists.")
    code = 409


class FirewallBypassNotFound(ResourceNotFound):
    message = _("FirewallBypass %(id)s could not be found.")

class FirewallBypassExists(FailureMessage):
    message = _("FirewallBypass for router_id : %(router_id)s, core_router_id : %(core_router_id)s already exists.")
    code = 409


class RouteEntryExists(FailureMessage):
    message = _("RouteEntry for src_router : %(src_router)s, nxt_router : %(nxt_router)s already exists.")
    code = 409


class RouteEntryNotFound(ResourceNotFound):
    message = _("RouteEntry %(id)s could not be found.")



