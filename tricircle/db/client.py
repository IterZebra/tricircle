# Copyright 2015 Huawei Technologies Co., Ltd.
# All Rights Reserved
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

import collections
import functools
import inspect
import six
import uuid

from keystoneclient.auth.identity import v3 as auth_identity
from keystoneclient.auth import token_endpoint
from keystoneclient import session
from keystoneclient.v3 import client as keystone_client
from oslo_config import cfg
from oslo_log import log as logging

import tricircle.common.context as tricircle_context
from tricircle.db import exception
from tricircle.db import models
from tricircle.db import resource_handle

client_opts = [
    cfg.StrOpt('auth_url',
               default='http://127.0.0.1:5000/v3',
               help='keystone authorization url'),
    cfg.StrOpt('identity_url',
               default='http://127.0.0.1:35357/v3',
               help='keystone service url'),
    cfg.BoolOpt('auto_refresh_endpoint',
                default=False,
                help='if set to True, endpoint will be automatically'
                     'refreshed if timeout accessing endpoint'),
    cfg.StrOpt('top_site_name',
               help='name of top site which client needs to access'),
    cfg.StrOpt('admin_username',
               help='username of admin account, needed when'
                    ' auto_refresh_endpoint set to True'),
    cfg.StrOpt('admin_password',
               help='password of admin account, needed when'
                    ' auto_refresh_endpoint set to True'),
    cfg.StrOpt('admin_tenant',
               help='tenant name of admin account, needed when'
                    ' auto_refresh_endpoint set to True'),
    cfg.StrOpt('admin_user_domain_name',
               default='Default',
               help='user domain name of admin account, needed when'
                    ' auto_refresh_endpoint set to True'),
    cfg.StrOpt('admin_tenant_domain_name',
               default='Default',
               help='tenant domain name of admin account, needed when'
                    ' auto_refresh_endpoint set to True')
]
client_opt_group = cfg.OptGroup('client')
cfg.CONF.register_group(client_opt_group)
cfg.CONF.register_opts(client_opts, group=client_opt_group)

LOG = logging.getLogger(__name__)


def _safe_operation(operation_name):
    def handle_func(func):
        @six.wraps(func)
        def handle_args(*args, **kwargs):
            instance, resource, context = args[:3]
            if resource not in instance.operation_resources_map[
                    operation_name]:
                raise exception.ResourceNotSupported(resource, operation_name)
            retries = 1
            for _ in xrange(retries + 1):
                try:
                    service = instance.resource_service_map[resource]
                    instance._ensure_endpoint_set(context, service)
                    return func(*args, **kwargs)
                except exception.EndpointNotAvailable as e:
                    if cfg.CONF.client.auto_refresh_endpoint:
                        LOG.warn(e.message + ', update endpoint and try again')
                        instance._update_endpoint_from_keystone(context, True)
                    else:
                        raise
        return handle_args
    return handle_func


class Client(object):
    def __init__(self):
        self.auth_url = cfg.CONF.client.auth_url
        self.resource_service_map = {}
        self.operation_resources_map = collections.defaultdict(set)
        self.service_handle_map = {}
        for _, handle_class in inspect.getmembers(resource_handle):
            if not inspect.isclass(handle_class):
                continue
            if not hasattr(handle_class, 'service_type'):
                continue
            handle_obj = handle_class(self.auth_url)
            self.service_handle_map[handle_obj.service_type] = handle_obj
            for resource in handle_obj.support_resource:
                self.resource_service_map[resource] = handle_obj.service_type
                for operation, index in six.iteritems(
                        resource_handle.operation_index_map):
                    # add parentheses to emphasize we mean to do bitwise and
                    if (handle_obj.support_resource[resource] & index) == 0:
                        continue
                    self.operation_resources_map[operation].add(resource)
                    setattr(self, '%s_%ss' % (operation, resource),
                            functools.partial(
                                getattr(self, '%s_resources' % operation),
                                resource))

    def _get_keystone_session(self):
        auth = auth_identity.Password(
            auth_url=cfg.CONF.client.identity_url,
            username=cfg.CONF.client.admin_username,
            password=cfg.CONF.client.admin_password,
            project_name=cfg.CONF.client.admin_tenant,
            user_domain_name=cfg.CONF.client.admin_user_domain_name,
            project_domain_name=cfg.CONF.client.admin_tenant_domain_name)
        return session.Session(auth=auth)

    def _get_admin_token(self):
        return self._get_keystone_session().get_token()

    def _get_admin_project_id(self):
        return self._get_keystone_session().get_project_id()

    def _get_endpoint_from_keystone(self, cxt):
        auth = token_endpoint.Token(cfg.CONF.client.identity_url,
                                    cxt.auth_token)
        sess = session.Session(auth=auth)
        cli = keystone_client.Client(session=sess)

        service_id_name_map = {}
        for service in cli.services.list():
            service_dict = service.to_dict()
            service_id_name_map[service_dict['id']] = service_dict['name']

        region_service_endpoint_map = {}
        for endpoint in cli.endpoints.list():
            endpoint_dict = endpoint.to_dict()
            if endpoint_dict['interface'] != 'public':
                continue
            region_id = endpoint_dict['region']
            service_id = endpoint_dict['service_id']
            url = endpoint_dict['url']
            service_name = service_id_name_map[service_id]
            if region_id not in region_service_endpoint_map:
                region_service_endpoint_map[region_id] = {}
            region_service_endpoint_map[region_id][service_name] = url
        return region_service_endpoint_map

    def _get_config_with_retry(self, cxt, filters, site, service, retry):
        conf_list = models.list_site_service_configurations(cxt, filters)
        if len(conf_list) > 1:
            raise exception.EndpointNotUnique(site, service)
        if len(conf_list) == 0:
            if not retry:
                raise exception.EndpointNotFound(site, service)
            self._update_endpoint_from_keystone(cxt, True)
            return self._get_config_with_retry(cxt,
                                               filters, site, service, False)
        return conf_list

    def _ensure_endpoint_set(self, cxt, service):
        handle = self.service_handle_map[service]
        if not handle.is_endpoint_url_set():
            site_filters = [{'key': 'site_name',
                             'comparator': 'eq',
                             'value': cfg.CONF.client.top_site_name}]
            site_list = models.list_sites(cxt, site_filters)
            if len(site_list) == 0:
                raise exception.ResourceNotFound(models.Site,
                                                 cfg.CONF.client.top_site_name)
            # site_name is unique key, safe to get the first element
            site_id = site_list[0]['site_id']
            config_filters = [
                {'key': 'site_id', 'comparator': 'eq', 'value': site_id},
                {'key': 'service_type', 'comparator': 'eq', 'value': service}]
            conf_list = self._get_config_with_retry(
                cxt, config_filters, site_id, service,
                cfg.CONF.client.auto_refresh_endpoint)
            url = conf_list[0]['service_url']
            handle.update_endpoint_url(url)

    def _update_endpoint_from_keystone(self, cxt, is_internal):
        """Update the database by querying service endpoint url from Keystone

        :param cxt: context object
        :param is_internal: if True, this method utilizes pre-configured admin
        username and password to apply an new admin token, this happens only
        when auto_refresh_endpoint is set to True. if False, token in cxt is
        directly used, users should prepare admin token themselves
        :return: None
        """
        if is_internal:
            admin_context = tricircle_context.Context()
            admin_context.auth_token = self._get_admin_token()
            endpoint_map = self._get_endpoint_from_keystone(admin_context)
        else:
            endpoint_map = self._get_endpoint_from_keystone(cxt)

        for region in endpoint_map:
            # use region name to query site
            site_filters = [{'key': 'site_name', 'comparator': 'eq',
                             'value': region}]
            site_list = models.list_sites(cxt, site_filters)
            # skip region/site not registered in cascade service
            if len(site_list) != 1:
                continue
            for service in endpoint_map[region]:
                site_id = site_list[0]['site_id']
                config_filters = [{'key': 'site_id', 'comparator': 'eq',
                                   'value': site_id},
                                  {'key': 'service_type', 'comparator': 'eq',
                                   'value': service}]
                config_list = models.list_site_service_configurations(
                    cxt, config_filters)

                if len(config_list) > 1:
                    raise exception.EndpointNotUnique(site_id, service)
                if len(config_list) == 1:
                    config_id = config_list[0]['service_id']
                    update_dict = {
                        'service_url': endpoint_map[region][service]}
                    models.update_site_service_configuration(
                        cxt, config_id, update_dict)
                else:
                    config_dict = {
                        'service_id': str(uuid.uuid4()),
                        'site_id': site_id,
                        'service_type': service,
                        'service_url': endpoint_map[region][service]
                    }
                    models.create_site_service_configuration(
                        cxt, config_dict)

    def get_endpoint(self, cxt, site_id, service):
        """Get endpoint url of given site and service

        :param cxt: context object
        :param site_id: site id
        :param service: service type
        :return: endpoint url for given site and service
        :raises: EndpointNotUnique, EndpointNotFound
        """
        config_filters = [
            {'key': 'site_id', 'comparator': 'eq', 'value': site_id},
            {'key': 'service_type', 'comparator': 'eq', 'value': service}]
        conf_list = self._get_config_with_retry(
            cxt, config_filters, site_id, service,
            cfg.CONF.client.auto_refresh_endpoint)
        return conf_list[0]['service_url']

    def update_endpoint_from_keystone(self, cxt):
        """Update the database by querying service endpoint url from Keystone

        Only admin should invoke this method since it requires admin token

        :param cxt: context object containing admin token
        :return: None
        """
        self._update_endpoint_from_keystone(cxt, False)

    @_safe_operation('list')
    def list_resources(self, resource, cxt, filters=None):
        """Query resource in site of top layer

        Directly invoke this method to query resources, or use
        list_(resource)s (self, cxt, filters=None), for example,
        list_servers (self, cxt, filters=None). These methods are
        automatically generated according to the supported resources
        of each ResourceHandle class.

        :param resource: resource type
        :param cxt: context object
        :param filters: list of dict with key 'key', 'comparator', 'value'
        like {'key': 'name', 'comparator': 'eq', 'value': 'private'}, 'key'
        is the field name of resources
        :return: list of dict containing resources information
        :raises: EndpointNotAvailable
        """
        if cxt.is_admin and not cxt.auth_token:
            cxt.auth_token = self._get_admin_token()
            cxt.tenant = self._get_admin_project_id()

        service = self.resource_service_map[resource]
        handle = self.service_handle_map[service]
        filters = filters or []
        return handle.handle_list(cxt, resource, filters)

    @_safe_operation('create')
    def create_resources(self, resource, cxt, *args, **kwargs):
        """Create resource in site of top layer

        Directly invoke this method to create resources, or use
        create_(resource)s (self, cxt, *args, **kwargs). These methods are
        automatically generated according to the supported resources of each
        ResourceHandle class.

        :param resource: resource type
        :param cxt: context object
        :param args, kwargs: passed according to resource type
               --------------------------
               resource -> args -> kwargs
               --------------------------
               aggregate -> name, availability_zone_name -> none
               --------------------------
        :return: a dict containing resource information
        :raises: EndpointNotAvailable
        """
        if cxt.is_admin and not cxt.auth_token:
            cxt.auth_token = self._get_admin_token()
            cxt.tenant = self._get_admin_project_id()

        service = self.resource_service_map[resource]
        handle = self.service_handle_map[service]
        return handle.handle_create(cxt, resource, *args, **kwargs)

    @_safe_operation('delete')
    def delete_resources(self, resource, cxt, resource_id):
        """Delete resource in site of top layer

        Directly invoke this method to delete resources, or use
        delete_(resource)s (self, cxt, obj_id). These methods are
        automatically generated according to the supported resources
        of each ResourceHandle class.
        :param resource: resource type
        :param cxt: context object
        :param resource_id: id of resource
        :return: None
        :raises: EndpointNotAvailable
        """
        if cxt.is_admin and not cxt.auth_token:
            cxt.auth_token = self._get_admin_token()
            cxt.tenant = self._get_admin_project_id()

        service = self.resource_service_map[resource]
        handle = self.service_handle_map[service]
        handle.handle_delete(cxt, resource, resource_id)

    @_safe_operation('action')
    def action_resources(self, resource, cxt, action, *args, **kwargs):
        """Apply action on resource in site of top layer

        Directly invoke this method to apply action, or use
        action_(resource)s (self, cxt, action, *args, **kwargs). These methods
        are automatically generated according to the supported resources of
        each ResourceHandle class.

        :param resource: resource type
        :param cxt: context object
        :param action: action applied on resource
        :param args, kwargs: passed according to resource type
               --------------------------
               resource -> action -> args -> kwargs
               --------------------------
               aggregate -> add_host -> aggregate, host -> none
               --------------------------
        :return: None
        :raises: EndpointNotAvailable
        """
        if cxt.is_admin and not cxt.auth_token:
            cxt.auth_token = self._get_admin_token()
            cxt.tenant = self._get_admin_project_id()

        service = self.resource_service_map[resource]
        handle = self.service_handle_map[service]
        return handle.handle_action(cxt, resource, action, *args, **kwargs)
