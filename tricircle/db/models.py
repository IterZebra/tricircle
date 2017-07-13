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

from oslo_db.sqlalchemy import models

import sqlalchemy as sql

from sqlalchemy import orm

from sqlalchemy.dialects import mysql
from sqlalchemy import schema

from tricircle.db import core
from tricircle.db import constants


def MediumText():
    return sql.Text().with_variant(mysql.MEDIUMTEXT(), 'mysql')
# Pod Model
class Pod(core.ModelBase, core.DictBase):
    __tablename__ = 'pods'
    attributes = ['pod_id', 'region_name', 'pod_az_name', 'dc_name', 'az_name']

    pod_id = sql.Column('pod_id', sql.String(length=36), primary_key=True)
    region_name = sql.Column('region_name', sql.String(length=255),
                             unique=True, nullable=False)
    pod_az_name = sql.Column('pod_az_name', sql.String(length=255),
                             nullable=True)
    dc_name = sql.Column('dc_name', sql.String(length=255), nullable=True)
    az_name = sql.Column('az_name', sql.String(length=255), nullable=False)


class CachedEndpoint(core.ModelBase, core.DictBase):
    __tablename__ = 'cached_endpoints'
    attributes = ['service_id', 'pod_id', 'service_type', 'service_url']

    service_id = sql.Column('service_id', sql.String(length=64),
                            primary_key=True)
    pod_id = sql.Column('pod_id', sql.String(length=36),
                        sql.ForeignKey('pods.pod_id'),
                        nullable=False)
    service_type = sql.Column('service_type', sql.String(length=64),
                              nullable=False)
    service_url = sql.Column('service_url', sql.String(length=512),
                             nullable=False)


# Routing Model
class ResourceRouting(core.ModelBase, core.DictBase, models.TimestampMixin):
    __tablename__ = 'resource_routings'
    __table_args__ = (
        schema.UniqueConstraint(
            'top_id', 'pod_id', 'resource_type',
            name='resource_routings0top_id0pod_id0resource_type'),
    )
    attributes = ['id', 'top_id', 'bottom_id', 'pod_id', 'project_id',
                  'resource_type', 'created_at', 'updated_at']

    # sqlite doesn't support auto increment on big integers so we use big int
    # for everything but sqlite
    id = sql.Column(sql.BigInteger().with_variant(sql.Integer(), 'sqlite'),
                    primary_key=True, autoincrement=True)
    top_id = sql.Column('top_id', sql.String(length=127), nullable=False)
    bottom_id = sql.Column('bottom_id', sql.String(length=36), index=True)
    pod_id = sql.Column('pod_id', sql.String(length=36),
                        sql.ForeignKey('pods.pod_id'),
                        nullable=False)
    project_id = sql.Column('project_id', sql.String(length=36))
    resource_type = sql.Column('resource_type', sql.String(length=64),
                               nullable=False)


class AsyncJob(core.ModelBase, core.DictBase):
    __tablename__ = 'async_jobs'
    __table_args__ = (
        schema.UniqueConstraint(
            'type', 'status', 'resource_id', 'extra_id',
            name='async_jobs0type0status0resource_id0extra_id'),
    )

    attributes = ['id', 'project_id', 'type', 'timestamp', 'status',
                  'resource_id', 'extra_id']

    id = sql.Column('id', sql.String(length=36), primary_key=True)
    project_id = sql.Column('project_id', sql.String(length=36))
    type = sql.Column('type', sql.String(length=36))
    timestamp = sql.Column('timestamp', sql.TIMESTAMP,
                           server_default=sql.text('CURRENT_TIMESTAMP'),
                           index=True)
    status = sql.Column('status', sql.String(length=36))
    resource_id = sql.Column('resource_id', sql.String(length=127))
    extra_id = sql.Column('extra_id', sql.String(length=36))


class AsyncJobLog(core.ModelBase, core.DictBase):
    __tablename__ = 'async_job_logs'

    attributes = ['id', 'project_id', 'resource_id', 'type', 'timestamp']

    id = sql.Column('id', sql.String(length=36), primary_key=True)
    project_id = sql.Column('project_id', sql.String(length=36))
    resource_id = sql.Column('resource_id', sql.String(length=127))
    type = sql.Column('type', sql.String(length=36))
    timestamp = sql.Column('timestamp', sql.TIMESTAMP,
                           server_default=sql.text('CURRENT_TIMESTAMP'),
                           index=True)


class ShadowAgent(core.ModelBase, core.DictBase):
    __tablename__ = 'shadow_agents'
    __table_args__ = (
        schema.UniqueConstraint(
            'host', 'type',
            name='host0type'),
    )

    attributes = ['id', 'pod_id', 'host', 'type', 'tunnel_ip']

    id = sql.Column('id', sql.String(length=36), primary_key=True)
    pod_id = sql.Column('pod_id', sql.String(length=36),
                        sql.ForeignKey('pods.pod_id'),
                        nullable=False)
    host = sql.Column('host', sql.String(length=255), nullable=False)
    type = sql.Column('type', sql.String(length=36), nullable=False)
    # considering IPv6 address, set the length to 48
    tunnel_ip = sql.Column('tunnel_ip', sql.String(length=48), nullable=False)


class RecycleResources(core.ModelBase, core.DictBase):
    __tablename__ = 'recycle_resources'

    attributes = ['resource_id', 'resource_type', 'project_id']

    resource_id = sql.Column('resource_id',
                             sql.String(length=36), primary_key=True)
    resource_type = sql.Column('resource_type',
                               sql.String(length=64), nullable=False)
    project_id = sql.Column('project_id',
                            sql.String(length=36), nullable=False, index=True)

class CoreRouterRoute(core.ModelBase, core.DictBase):
    __tablename__ = 'core_routerroutes'
    attributes = ['core_router_id','destination', 'nexthop']
    destination = sql.Column(sql.String(64), nullable=False, primary_key=True)
    nexthop = sql.Column(sql.String(64), nullable=False, primary_key=True)
    core_router_id = sql.Column(sql.String(36),
                          sql.ForeignKey('core_routers.id',
                                        ondelete="CASCADE"),
                          primary_key=True)


class CoreRouterInterface(core.ModelBase, core.DictBase):
    __tablename__ = 'core_router_interfaces'
    attributes = ['interface_id','core_router_id','fabric','project_id']
    interface_id = sql.Column('interface_id',
                             sql.String(length=36), primary_key=True)
    core_router_id = sql.Column(sql.String(36),
                          sql.ForeignKey('core_routers.id',
                                        ondelete="CASCADE"))
    fabric= sql.Column('fabric', sql.String(length=255), nullable=False)
    project_id= sql.Column('project_id', sql.String(length=36), nullable=False)

class DCI(core.ModelBase, core.DictBase):
    __tablename__ = 'dcis'
    attributes = ['id','fabric', 'router_id', 'dci_peering_id',
                  'type','name','project_id', 'admin_state_up',
                  'description', 'status']
    id= sql.Column('id', sql.String(length=36), primary_key=True)
    fabric= sql.Column('fabric', sql.String(length=255), nullable=False)
    router_id = sql.Column('router_id', sql.String(length=36), nullable=False)
    dci_peering_id = sql.Column('dci_peering_id', sql.String(length=36), nullable=False)
    type= sql.Column('type',sql.String(16), nullable=False)
    name= sql.Column('name', sql.String(length=255), nullable=False)
    project_id= sql.Column('project_id', sql.String(length=36), nullable=False)
    admin_state_up = sql.Column(sql.Boolean(), nullable=False)
    description = sql.Column('description', sql.String(length=255), nullable=True)
    status= sql.Column('status',sql.String(16), nullable=False, server_default=constants.DOWN_STATUS)
    #local_router_id= sql.Column('local_router_id',sql.String(36),
    #                      sql.ForeignKey('core_routers.id',
    #                                    ondelete="CASCADE"))

class DynamicPeeringConnection(core.ModelBase, core.DictBase):
    __tablename__ = 'dynamic_peering_connections'
    attributes = ['dynamic_peering_connection_id', 'local_router_id', 'peering_router_id',
                  'dynamic_peering_connection_name', 'project_id', 'admin_state_up', 
                  'description', 'status']
    dynamic_peering_connection_id = sql.Column('dynamic_peering_connection_id', sql.String(length=36), primary_key=True)
    dynamic_peering_connection_name= sql.Column('dynamic_peering_connection_name', sql.String(length=255), nullable=False)
    peering_router_id = sql.Column('peering_router_id', sql.String(length=36), nullable=False)
    #local_router_id = sql.Column('local_router_id', sql.String(length=36), nullable=False)
    project_id= sql.Column('project_id', sql.String(length=36), nullable=False)
    admin_state_up = sql.Column(sql.Boolean(), nullable=False)
    description = sql.Column('description', sql.String(length=255), nullable=True)
    status= sql.Column('status',sql.String(16), nullable=False, server_default=constants.DOWN_STATUS)
    local_router_id= sql.Column('local_router_id',sql.String(36),
                          sql.ForeignKey('core_routers.id',
                                        ondelete="CASCADE"))
    #peering_router_id= sql.Column('peering_router_id',sql.String(36),
    #                      sql.ForeignKey('core_routers.id',
    #                                    ondelete="CASCADE"),
    #                      primary_key=True)


class FirewallGateway(core.ModelBase, core.DictBase):
    __tablename__ = 'firewall_gateways'
    attributes = ['id','fabric','firewall_id', 'router_id', 'project_id',
                  'admin_state_up', 'description', 'status']

    id= sql.Column('id', sql.String(length=36), primary_key=True)
    fabric= sql.Column('fabric', sql.String(length=255), nullable=False)
    firewall_id = sql.Column('firewall_id', sql.String(length=36), primary_key=False)
    router_id= sql.Column('router_id', sql.String(length=36), primary_key=False)
    project_id= sql.Column('project_id', sql.String(length=36), nullable=False)
    admin_state_up = sql.Column(sql.Boolean(), nullable=False)
    status= sql.Column('status',sql.String(16), nullable=False, server_default=constants.DOWN_STATUS)
    description = sql.Column('description', sql.String(length=255), nullable=True)


class FirewallBypass(core.ModelBase, core.DictBase):
    __tablename__ = 'firewall_bypasss'
    attributes = ['id', 'fabric', 'core_router_id',
                  'router_id', 'project_id',
                  'admin_state_up', 'description', 'status']

    id= sql.Column('id', sql.String(length=36), primary_key=True)
    fabric= sql.Column('fabric', sql.String(length=255), nullable=False)
    router_id= sql.Column('router_id', sql.String(length=36), primary_key=False)
    project_id= sql.Column('project_id', sql.String(length=36), nullable=False)
    admin_state_up = sql.Column(sql.Boolean(), nullable=False)
    status= sql.Column('status',sql.String(16), nullable=False, server_default=constants.DOWN_STATUS)
    description = sql.Column('description', sql.String(length=255), nullable=True)
    core_router_id= sql.Column('core_router_id',sql.String(36),
                          sql.ForeignKey('core_routers.id',
                                        ondelete="CASCADE"))

# Core Router Model
class CoreRouter(core.ModelBase, core.DictBase):
    __tablename__ = 'core_routers'
    attributes = ['id', 'dc', 'project_id', 'core_router_name',
                  'admin_state_up', 'description', 'status']

    id = sql.Column('id', sql.String(length=36), primary_key=True)
    dc= sql.Column('dc', sql.String(length=255), nullable=False)
    project_id= sql.Column('project_id', sql.String(length=36), nullable=False)
    core_router_name= sql.Column('core_router_name', sql.String(length=255), nullable=False)
    admin_state_up = sql.Column(sql.Boolean(), nullable=False)
    description = sql.Column('description', sql.String(length=255), nullable=True)
    status= sql.Column('status',sql.String(16), nullable=False, server_default=constants.DOWN_STATUS)
    routes = orm.relationship(CoreRouterRoute,
                              backref='core_router',
                              cascade='all, delete, delete-orphan',
                              lazy='subquery')
    interfaces = orm.relationship(CoreRouterInterface,
                              backref='core_router',
                              cascade='all, delete, delete-orphan',
                              lazy='subquery')
    firewall_bypasss= orm.relationship(FirewallBypass,
                              backref='core_router',
                              cascade='all, delete, delete-orphan',
                              lazy='subquery')

class TricircleResource(core.ModelBase, core.DictBase, models.TimestampMixin):
    __tablename__ = 'tricircle_resources'
    attributes = ['id', 'region_name','project_id','name','status','admin_state_up',
                  'resource_type', 'created_at', 'updated_at']

    id= sql.Column('id', sql.String(length=36), primary_key=True)
    name= sql.Column('name', sql.String(length=255), nullable=False)
    region_name= sql.Column('region_name', sql.String(length=255), nullable=False)
    project_id = sql.Column('project_id', sql.String(length=36),nullable=False)
    resource_type = sql.Column('resource_type', sql.String(length=64),
                               nullable=False)
    status = sql.Column('status', sql.String(length=36))
    admin_state_up = sql.Column(sql.Boolean(), nullable=False)

class Fabric(core.ModelBase, core.DictBase):
    __tablename__ = 'fabrics'
    attributes = ['id', 'dc_id', 'fabric_name']

    id = sql.Column('id', sql.String(length=36), primary_key=True)
    dc_id = sql.Column('dc_id', sql.String(length=36),
                        sql.ForeignKey('dcs.id'),
                        nullable=False)
    fabric_name = sql.Column('fabric_name', sql.String(length=255),
                             unique=True, nullable=False)

class DC(core.ModelBase, core.DictBase):
    __tablename__ = 'dcs'
    attributes = ['id', 'region_id', 'dc_name']

    id = sql.Column('id', sql.String(length=36), primary_key=True)
    region_id = sql.Column('region_id', sql.String(length=36),
                        sql.ForeignKey('regions.id'),
                        nullable=False)
    dc_name= sql.Column('dc_name', sql.String(length=255),
                             unique=True, nullable=False)
    fabrics = orm.relationship(Fabric,
                              backref='dc',
                              cascade='all, delete, delete-orphan',
                              lazy='subquery')
 
class Region(core.ModelBase, core.DictBase):
    __tablename__ = 'regions'
    attributes = ['id', 'region_name']

    id = sql.Column('id', sql.String(length=36), primary_key=True)
    region_name = sql.Column('region_name', sql.String(length=255),
                             unique=True, nullable=False)
    dcs= orm.relationship(DC,backref='region',
                              cascade='all, delete, delete-orphan',
                              lazy='subquery')

class DestinationCidr(core.ModelBase, core.DictBase):
    __tablename__ = 'destination_cidrs'
    attributes = ['destination']
    destination = sql.Column(sql.String(64), nullable=False, primary_key=True)
    route_entry_id= sql.Column('route_entry_id',sql.String(36),
                                        sql.ForeignKey('route_entries.id',
                                        ondelete="CASCADE"),primary_key=True)


class RouteEntry(core.ModelBase, core.DictBase):
    __tablename__ = 'route_entries'
    attributes = ['id','src_router','nxt_router','project_id',
                   'status','admin_state_up','description','destination_cidr_list']
    id= sql.Column('id', sql.String(length=36), primary_key=True)
    src_router= sql.Column('src_router', sql.String(length=36), nullable=False)
    nxt_router= sql.Column('nxt_router', sql.String(length=36), nullable=False)
    project_id = sql.Column('project_id', sql.String(length=36),nullable=False)
    admin_state_up = sql.Column(sql.Boolean(), nullable=False)
    status= sql.Column('status',sql.String(16), nullable=False, server_default=constants.DOWN_STATUS)
    description = sql.Column('description', sql.String(length=255), nullable=True)
    destination_cidr_list= orm.relationship(DestinationCidr,backref='route_entry',
                              cascade='all, delete, delete-orphan',
                              lazy='subquery')

