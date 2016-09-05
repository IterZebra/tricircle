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

import copy
import mock
from mock import patch
import six
import unittest

from oslo_utils import uuidutils

import neutron_lib.constants as q_constants
import neutron_lib.exceptions as q_exceptions

from tricircle.common import constants
import tricircle.common.context as t_context
import tricircle.network.local_plugin as plugin


TOP_NETS = []
TOP_SUBNETS = []
TOP_PORTS = []
BOTTOM_NETS = []
BOTTOM_SUBNETS = []
BOTTOM_PORTS = []
RES_LIST = [TOP_NETS, TOP_SUBNETS, TOP_PORTS,
            BOTTOM_NETS, BOTTOM_SUBNETS, BOTTOM_PORTS]
RES_MAP = {'network': {True: TOP_NETS, False: BOTTOM_NETS},
           'subnet': {True: TOP_SUBNETS, False: BOTTOM_SUBNETS},
           'port': {True: TOP_PORTS, False: BOTTOM_PORTS}}


def create_resource(_type, is_top, body):
    RES_MAP[_type][is_top].append(body)


def update_resource(_type, is_top, resource_id, body):
    for resource in RES_MAP[_type][is_top]:
        if resource['id'] == resource_id:
            resource.update(body)
            return copy.deepcopy(resource)
    raise q_exceptions.NotFound()


def get_resource(_type, is_top, resource_id):
    for resource in RES_MAP[_type][is_top]:
        if resource['id'] == resource_id:
            return copy.deepcopy(resource)
    raise q_exceptions.NotFound()


def list_resource(_type, is_top, filters=None):
    if not filters:
        return [copy.deepcopy(resource) for resource in RES_MAP[_type][is_top]]
    ret = []
    for resource in RES_MAP[_type][is_top]:
        pick = True
        for key, value in six.iteritems(filters):
            if resource.get(key) not in value:
                pick = False
                break
        if pick:
            ret.append(copy.deepcopy(resource))
    return ret


def delete_resource(_type, is_top, body):
    RES_MAP[_type][is_top].append(body)


class FakeCorePlugin(object):
    def create_network(self, context, network):
        create_resource('network', False, network['network'])
        return network['network']

    def get_network(self, context, _id, fields=None):
        return get_resource('network', False, _id)

    def get_networks(self, context, filters=None, fields=None, sorts=None,
                     limit=None, marker=None, page_reverse=False):
        return list_resource('network', False, filters)

    def create_subnet(self, context, subnet):
        create_resource('subnet', False, subnet['subnet'])
        return subnet['subnet']

    def update_subnet(self, context, _id, subnet):
        return update_resource('subnet', False, _id, subnet['subnet'])

    def get_subnet(self, context, _id, fields=None):
        return get_resource('subnet', False, _id)

    def create_port(self, context, port):
        create_resource('port', False, port['port'])
        return port['port']

    def get_port(self, context, _id, fields=None):
        return get_resource('port', False, _id)

    def get_ports(self, context, filters=None, fields=None, sorts=None,
                  limit=None, marker=None, page_reverse=False):
        return list_resource('port', False, filters)


class FakeSession(object):
    class WithWrapper(object):
        def __enter__(self):
            pass

        def __exit__(self, type, value, traceback):
            pass

    def begin(self, subtransactions=True):
        return FakeSession.WithWrapper()


class FakeContext(object):
    def __init__(self):
        self.session = FakeSession()


class FakeClient(object):
    def list_networks(self, **kwargs):
        return {'networks': list_resource('network', True, kwargs)}

    def create_port(self, port):
        if 'id' not in port['port']:
            port['port']['id'] = uuidutils.generate_uuid()
        if 'fixed_ips' not in port['port']:
            for subnet in TOP_SUBNETS:
                if subnet['network_id'] == port['port']['network_id']:
                    ip = {'subnet_id': subnet['id'],
                          'ip_address': subnet['cidr'][:-4] + '3'}
                    port['port']['fixed_ips'] = [ip]
        create_resource('port', True, port['port'])
        return port

    def show_port(self, port_id):
        return {'port': get_resource('port', True, port_id)}

    def list_ports(self, **kwargs):
        def find_ip_address(port, ip_address):
            for ip in port.get('fixed_ips', []):
                if ip['ip_address'] == ip_address:
                    return True
            return False

        ports = []
        for port in TOP_PORTS:
            pick = True
            for key, value in six.iteritems(kwargs):
                if key == 'fixed_ips':
                    if not find_ip_address(port, value.split('=')[1]):
                        pick = False
                        break
                elif port.get(key) != value:
                    pick = False
                    break
            if pick:
                ports.append(copy.deepcopy(port))
        return {'ports': ports}


class FakeNeutronHandle(object):
    def _get_client(self, context):
        return FakeClient()

    def handle_get(self, context, _type, _id):
        return get_resource(_type, True, _id)


class FakePlugin(plugin.TricirclePlugin):
    def __init__(self):
        self.core_plugin = FakeCorePlugin()
        self.neutron_handle = FakeNeutronHandle()


class PluginTest(unittest.TestCase):
    def setUp(self):
        self.tenant_id = uuidutils.generate_uuid()
        self.plugin = FakePlugin()
        self.context = FakeContext()

    def _prepare_resource(self):
        network_id = uuidutils.generate_uuid()
        subnet_id = uuidutils.generate_uuid()
        port_id = uuidutils.generate_uuid()
        t_net = {'id': network_id,
                 'tenant_id': self.tenant_id,
                 'name': 'net1',
                 'provider:network_type': constants.NT_SHARED_VLAN,
                 'subnets': [subnet_id]}
        t_subnet = {'id': subnet_id,
                    'tenant_id': self.tenant_id,
                    'name': 'subnet1',
                    'network_id': network_id,
                    'cidr': '10.0.1.0/24',
                    'enable_dhcp': True}
        t_port = {'id': port_id,
                  'tenant_id': self.tenant_id,
                  'admin_state_up': True,
                  'name': constants.dhcp_port_name % subnet_id,
                  'network_id': network_id,
                  'mac_address': 'fa:16:3e:96:41:02',
                  'device_owner': 'network:dhcp',
                  'device_id': 'reserved_dhcp_port',
                  'fixed_ips': [{'subnet_id': subnet_id,
                                 'ip_address': '10.0.1.2'}],
                  'binding:profile': {}}
        TOP_NETS.append(t_net)
        TOP_SUBNETS.append(t_subnet)
        TOP_PORTS.append(t_port)
        return t_net, t_subnet, t_port

    def _validate(self, net, subnet, port):
        b_net = self.plugin.get_network(self.context, net['id'])
        net.pop('provider:network_type')
        b_net_type = b_net.pop('provider:network_type')
        b_subnet = get_resource('subnet', False, subnet['id'])
        b_port = get_resource('port', False, port['id'])
        b_net.pop('project_id')
        b_subnet.pop('project_id')
        port.pop('name')
        b_port.pop('name')
        self.assertDictEqual(net, b_net)
        self.assertDictEqual(subnet, b_subnet)
        self.assertEqual('vlan', b_net_type)
        self.assertDictEqual(port, b_port)

    @patch.object(t_context, 'get_context_from_neutron_context', new=mock.Mock)
    def test_get_network(self):
        t_net, t_subnet, t_port = self._prepare_resource()
        self._validate(t_net, t_subnet, t_port)

    @patch.object(t_context, 'get_context_from_neutron_context', new=mock.Mock)
    def test_get_networks(self):
        t_net1, t_subnet1, t_port1 = self._prepare_resource()
        t_net2, t_subnet2, t_port2 = self._prepare_resource()
        self.plugin.get_networks(self.context,
                                 {'id': [t_net1['id'], t_net2['id'],
                                         'fake_net_id']})
        self._validate(t_net1, t_subnet1, t_port1)
        self._validate(t_net2, t_subnet2, t_port2)

    @patch.object(t_context, 'get_context_from_neutron_context', new=mock.Mock)
    def test_create_port(self):
        t_net, t_subnet, t_port = self._prepare_resource()
        port = {
            'port': {'network_id': t_net['id'],
                     'fixed_ips': q_constants.ATTR_NOT_SPECIFIED}
        }
        t_port = self.plugin.create_port(self.context, port)
        b_port = get_resource('port', False, t_port['id'])
        self.assertDictEqual(t_port, b_port)

    @patch.object(t_context, 'get_context_from_neutron_context', new=mock.Mock)
    def test_create_port_ip_specified(self):
        t_net, t_subnet, t_port = self._prepare_resource()
        port_body = {
            'port': {'network_id': t_net['id'],
                     'fixed_ips': [{'ip_address': '10.0.1.4'}]}
        }
        self.assertRaises(q_exceptions.InvalidIpForNetwork,
                          self.plugin.create_port, self.context, port_body)

        port_id = uuidutils.generate_uuid()
        t_port = {'id': port_id,
                  'tenant_id': self.tenant_id,
                  'admin_state_up': True,
                  'network_id': t_net['id'],
                  'mac_address': 'fa:16:3e:96:41:04',
                  'fixed_ips': [{'subnet_id': t_subnet['id'],
                                 'ip_address': '10.0.1.4'}],
                  'binding:profile': {}}
        TOP_PORTS.append(t_port)
        b_port = self.plugin.create_port(self.context, port_body)
        self.assertDictEqual(t_port, b_port)

    @patch.object(t_context, 'get_context_from_neutron_context', new=mock.Mock)
    def test_get_port(self):
        t_net, t_subnet, t_port = self._prepare_resource()
        port_id = uuidutils.generate_uuid()
        t_port = {'id': port_id,
                  'tenant_id': self.tenant_id,
                  'admin_state_up': True,
                  'network_id': t_net['id'],
                  'mac_address': 'fa:16:3e:96:41:04',
                  'fixed_ips': [{'subnet_id': t_subnet['id'],
                                 'ip_address': '10.0.1.4'}],
                  'binding:profile': {}}
        TOP_PORTS.append(t_port)
        t_port = self.plugin.get_port(self.context, port_id)
        b_port = get_resource('port', False, t_port['id'])
        self.assertDictEqual(t_port, b_port)

    @patch.object(t_context, 'get_context_from_neutron_context', new=mock.Mock)
    def test_get_ports(self):
        t_net, t_subnet, t_port = self._prepare_resource()
        t_ports = []
        for i in (4, 5):
            port_id = uuidutils.generate_uuid()
            t_port = {'id': port_id,
                      'tenant_id': self.tenant_id,
                      'admin_state_up': True,
                      'network_id': t_net['id'],
                      'mac_address': 'fa:16:3e:96:41:04',
                      'fixed_ips': [{'subnet_id': t_subnet['id'],
                                     'ip_address': '10.0.1.%d' % i}],
                      'binding:profile': {}}
            TOP_PORTS.append(t_port)
            t_ports.append(t_port)
        self.plugin.get_ports(self.context,
                              {'id': [t_ports[0]['id'], t_ports[1]['id'],
                                      'fake_port_id']})
        for i in (0, 1):
            b_port = get_resource('port', False, t_ports[i]['id'])
            b_port.pop('project_id')
            self.assertDictEqual(t_ports[i], b_port)

    def tearDown(self):
        for res in RES_LIST:
            del res[:]
