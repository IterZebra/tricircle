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


import migrate
import sqlalchemy as sql


def upgrade(migrate_engine):
    meta = sql.MetaData()
    meta.bind = migrate_engine

    regions= sql.Table(
        'regions', meta,
        sql.Column('id', sql.String(length=36), nullable=False,primary_key=True),
        sql.Column('region_name', sql.String(length=255), nullable=False),
        sql.UniqueConstraint('region_name'),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    dcs= sql.Table(
        'dcs', meta,
        sql.Column('id', sql.String(length=36), nullable=False,primary_key=True),
        sql.Column('dc_name', sql.String(length=255), nullable=False),
        sql.Column('region_id', sql.String(length=255), nullable=False),
        sql.ForeignKeyConstraint(['region_id'], ['regions.id']),
        sql.UniqueConstraint('dc_name'),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    fabrics= sql.Table(
        'fabrics', meta,
        sql.Column('id', sql.String(length=36), nullable=False,primary_key=True),
        sql.Column('fabric_name', sql.String(length=255), nullable=False),
        sql.Column('dc_id', sql.String(length=255), nullable=False),
        sql.ForeignKeyConstraint(['dc_id'], ['dcs.id']),
        sql.UniqueConstraint('fabric_name'),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    core_routers = sql.Table(
        'core_routers', meta,
        sql.Column('id', sql.String(length=36), primary_key=True),
        sql.Column('dc', sql.String(length=255), nullable=False),
        sql.Column('project_id', sql.String(length=36), nullable=False),
        sql.Column('core_router_name', sql.String(length=255), nullable=False),
        sql.Column('admin_state_up', sql.Boolean(),
                  nullable=False, server_default=sql.true()),
        sql.Column('description', sql.String(length=255), nullable=True),
        sql.Column('status', sql.String(length=16),nullable=False),
        #TODO
        sql.UniqueConstraint('dc'),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    tricircle_resources = sql.Table(
        'tricircle_resources', meta,
        sql.Column('id', sql.String(length=36), nullable=False,primary_key=True),
        sql.Column('name', sql.String(length=255), nullable=False),
        sql.Column('region_name', sql.String(length=255), nullable=False),
        sql.Column('project_id', sql.String(length=36), nullable=False),
        sql.Column('resource_type', sql.String(length=64), nullable=False),
        sql.Column('created_at', sql.DateTime),
        sql.Column('updated_at', sql.DateTime),
        sql.Column('admin_state_up', sql.Boolean(),
                  nullable=False, server_default=sql.true()),
        sql.Column('status', sql.String(length=16),nullable=False),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    core_routerroutes = sql.Table(
        'core_routerroutes', meta,
        sql.Column('destination', sql.String(length=64), nullable=False),
        sql.Column('nexthop', sql.String(length=64), nullable=False),
        sql.Column('core_router_id', sql.String(length=36), nullable=False),
        sql.ForeignKeyConstraint(['core_router_id'], ['core_routers.id'],
                                ondelete='CASCADE'),
        sql.PrimaryKeyConstraint('destination', 'nexthop', 'core_router_id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8')


    route_entries= sql.Table(
        'route_entries', meta,
        sql.Column('id', sql.String(length=36), primary_key=True),
        sql.Column('src_router', sql.String(length=36), nullable=False),
        sql.Column('nxt_router', sql.String(length=36), nullable=False),
        sql.Column('project_id', sql.String(length=36), nullable=False),
        sql.Column('admin_state_up', sql.Boolean(),
                  nullable=False, server_default=sql.true()),
        sql.Column('description', sql.String(length=255), nullable=True),
        sql.Column('status', sql.String(length=16),nullable=False),
        #sql.UniqueConstraint('src_router'),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    destination_cidrs= sql.Table(
        'destination_cidrs', meta,
        sql.Column('destination', sql.String(length=64), nullable=False),
        sql.Column('route_entry_id', sql.String(length=36), nullable=False),
        sql.ForeignKeyConstraint(['route_entry_id'], ['route_entries.id'],
                                ondelete='CASCADE'),
        sql.PrimaryKeyConstraint('destination','route_entry_id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8')


    core_router_interfaces = sql.Table(
        'core_router_interfaces', meta,
        sql.Column('interface_id', sql.String(length=36), nullable=False),
        sql.Column('core_router_id', sql.String(length=36), nullable=False),
        sql.Column('fabric', sql.String(length=255), nullable=False),
        sql.Column('project_id', sql.String(length=36), nullable=False),
        sql.ForeignKeyConstraint(['core_router_id'], ['core_routers.id']),
        sql.PrimaryKeyConstraint('interface_id'),
        sql.UniqueConstraint('core_router_id','fabric'),
        sql.UniqueConstraint('fabric'),
        mysql_engine='InnoDB',
        mysql_charset='utf8')


    dcis= sql.Table(
        'dcis', meta,
        sql.Column('id', sql.String(length=36), primary_key=True),
        sql.Column('fabric', sql.String(length=255), nullable=False),
        sql.Column('router_id', sql.String(length=36), nullable=False),
        sql.Column('dci_peering_id', sql.String(length=36), nullable=False),
        sql.Column('project_id', sql.String(length=36), nullable=False),
        sql.Column('type', sql.String(length=16),nullable=False),
        sql.Column('name', sql.String(length=255), nullable=False),
        sql.Column('admin_state_up', sql.Boolean(),
                  nullable=False, server_default=sql.true()),
        sql.Column('status', sql.String(length=16),nullable=False),
        sql.Column('description', sql.String(length=255), nullable=True),
        sql.UniqueConstraint('dci_peering_id','router_id','type'),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    dynamic_peering_connections = sql.Table(
        'dynamic_peering_connections', meta,
        sql.Column('dynamic_peering_connection_id', sql.String(length=36), primary_key=True),
        sql.Column('local_router_id', sql.String(length=36), nullable=False),
        sql.Column('peering_router_id', sql.String(length=36), nullable=False),
        sql.Column('project_id', sql.String(length=36), nullable=False),
        sql.Column('dynamic_peering_connection_name', sql.String(length=255), nullable=False),
        sql.Column('admin_state_up', sql.Boolean(),
                  nullable=False, server_default=sql.true()),
        sql.Column('status', sql.String(length=16),nullable=False),
        sql.Column('description', sql.String(length=255), nullable=True),
        sql.UniqueConstraint('local_router_id','peering_router_id'),
        sql.ForeignKeyConstraint(['local_router_id'], ['core_routers.id']), 
        sql.ForeignKeyConstraint(['peering_router_id'], ['core_routers.id']), 
        mysql_engine='InnoDB',
        mysql_charset='utf8')


    firewall_gateways= sql.Table(
        'firewall_gateways', meta,
        sql.Column('id', sql.String(length=36), primary_key=True),
        sql.Column('fabric', sql.String(length=255), nullable=False),
        sql.Column('router_id', sql.String(length=36), nullable=False),
        sql.Column('firewall_id', sql.String(length=36), nullable=False),
        sql.Column('project_id', sql.String(length=36), nullable=False),
        sql.Column('admin_state_up', sql.Boolean(),
                  nullable=False, server_default=sql.true()),
        sql.Column('status', sql.String(length=16),nullable=False),
        sql.Column('description', sql.String(length=255), nullable=True),
        sql.UniqueConstraint('router_id','firewall_id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8')


    firewall_bypasss= sql.Table(
        'firewall_bypasss', meta,
        sql.Column('id', sql.String(length=36), primary_key=True),
        sql.Column('fabric', sql.String(length=255), nullable=False),
        sql.Column('core_router_id', sql.String(length=36), nullable=False),
        sql.Column('router_id', sql.String(length=36), nullable=False),
        sql.Column('project_id', sql.String(length=36), nullable=False),
        sql.Column('admin_state_up', sql.Boolean(),
                  nullable=False, server_default=sql.true()),
        sql.Column('status', sql.String(length=16),nullable=False),
        sql.Column('description', sql.String(length=255), nullable=True),
        sql.ForeignKeyConstraint(['core_router_id'], ['core_routers.id']), 
        sql.UniqueConstraint('router_id','core_router_id'),
        mysql_engine='InnoDB',
        mysql_charset='utf8')

    tables = [regions,dcs,fabrics,dcis,tricircle_resources,
              core_routers,core_routerroutes,core_router_interfaces,
              route_entries,destination_cidrs,
              dynamic_peering_connections,firewall_gateways,firewall_bypasss]
    for table in tables:
        table.create()

def downgrade(migrate_engine):
    raise NotImplementedError('can not downgrade from init repo.')
