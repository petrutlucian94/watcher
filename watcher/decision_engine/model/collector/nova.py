# -*- encoding: utf-8 -*-
# Copyright (c) 2017 Intel Innovation and Research Ireland Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_log import log

from watcher.common import nova_helper
from watcher.decision_engine.model.collector import base
from watcher.decision_engine.model import element
from watcher.decision_engine.model import model_root
from watcher.decision_engine.model.notification import nova
from watcher.decision_engine.scope import compute as compute_scope

LOG = log.getLogger(__name__)


class NovaClusterDataModelCollector(base.BaseClusterDataModelCollector):
    """Nova cluster data model collector

    The Nova cluster data model collector creates an in-memory
    representation of the resources exposed by the compute service.
    """

    HOST_AGGREGATES = "#/items/properties/compute/host_aggregates/"
    SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "host_aggregates": {
                    "type": "array",
                    "items": {
                        "anyOf": [
                            {"$ref": HOST_AGGREGATES + "id"},
                            {"$ref": HOST_AGGREGATES + "name"},
                        ]
                    }
                },
                "availability_zones": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string"
                            }
                        },
                        "additionalProperties": False
                    }
                },
                "exclude": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "instances": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "uuid": {
                                            "type": "string"
                                        }
                                    },
                                    "additionalProperties": False
                                }
                            },
                            "compute_nodes": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string"
                                        }
                                    },
                                    "additionalProperties": False
                                }
                            },
                            "host_aggregates": {
                                "type": "array",
                                "items": {
                                    "anyOf": [
                                        {"$ref": HOST_AGGREGATES + "id"},
                                        {"$ref": HOST_AGGREGATES + "name"},
                                    ]
                                }
                            },
                            "instance_metadata": {
                                "type": "array",
                                "items": {
                                    "type": "object"
                                }
                            },
                            "projects": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "uuid": {
                                            "type": "string"
                                        }
                                    },
                                    "additionalProperties": False
                                }
                            }
                        },
                        "additionalProperties": False
                    }
                }
            },
            "additionalProperties": False
        },
        "host_aggregates": {
            "id": {
                "properties": {
                    "id": {
                        "oneOf": [
                            {"type": "integer"},
                            {"enum": ["*"]}
                        ]
                    }
                },
                "additionalProperties": False
            },
            "name": {
                "properties": {
                    "name": {
                        "type": "string"
                    }
                },
                "additionalProperties": False
            }
        },
        "additionalProperties": False
    }

    def __init__(self, config, osc=None):
        super(NovaClusterDataModelCollector, self).__init__(config, osc)

    @property
    def notification_endpoints(self):
        """Associated notification endpoints

        :return: Associated notification endpoints
        :rtype: List of :py:class:`~.EventsNotificationEndpoint` instances
        """
        return [
            nova.VersionedNotification(self),
        ]

    def get_audit_scope_handler(self, audit_scope):
        self._audit_scope_handler = compute_scope.ComputeScope(
            audit_scope, self.config)
        if self._data_model_scope is None or (
            len(self._data_model_scope) > 0 and (
                self._data_model_scope != audit_scope)):
            self._data_model_scope = audit_scope
            self._cluster_data_model = None
        LOG.debug("audit scope %s", audit_scope)
        return self._audit_scope_handler

    def execute(self):
        """Build the compute cluster data model"""
        LOG.debug("Building latest Nova cluster data model")

        if self._audit_scope_handler is None:
            LOG.debug("No audit, Don't Build compute data model")
            return

        builder = ModelBuilder(self.osc)
        return builder.execute(self._data_model_scope)


class ModelBuilder(object):
    """Build the graph-based model

    This model builder adds the following data"

    - Compute-related knowledge (Nova)
    - TODO(v-francoise): Storage-related knowledge (Cinder)
    - TODO(v-francoise): Network-related knowledge (Neutron)

    NOTE(v-francoise): This model builder is meant to be extended in the future
    to also include both storage and network information respectively coming
    from Cinder and Neutron. Some prelimary work has been done in this
    direction in https://review.opendev.org/#/c/362730 but since we cannot
    guarantee a sufficient level of consistency for neither the storage nor the
    network part before the end of the Ocata cycle, this work has been
    re-scheduled for Pike. In the meantime, all the associated code has been
    commented out.
    """

    def __init__(self, osc):
        self.osc = osc
        self.model = None
        self.model_scope = dict()
        self.no_model_scope_flag = False
        self.nova = osc.nova()
        self.nova_helper = nova_helper.NovaHelper(osc=self.osc)

    def _collect_aggregates(self, host_aggregates, _nodes):
        aggregate_list = self.nova_helper.get_aggregate_list()
        aggregate_ids = [aggregate['id'] for aggregate
                         in host_aggregates if 'id' in aggregate]
        aggregate_names = [aggregate['name'] for aggregate
                           in host_aggregates if 'name' in aggregate]
        include_all_nodes = any('*' in field
                                for field in (aggregate_ids, aggregate_names))

        for aggregate in aggregate_list:
            if (aggregate.id in aggregate_ids or
                aggregate.name in aggregate_names or
                    include_all_nodes):
                _nodes.update(aggregate.hosts)

    def _collect_zones(self, availability_zones, _nodes):
        service_list = self.nova_helper.get_service_list()
        zone_names = [zone['name'] for zone
                      in availability_zones]
        include_all_nodes = False
        if '*' in zone_names:
            include_all_nodes = True
        for service in service_list:
            if service.zone in zone_names or include_all_nodes:
                _nodes.add(service.host)

    def _add_physical_layer(self):
        """Add the physical layer of the graph.

        This includes components which represent actual infrastructure
        hardware.
        """
        compute_nodes = set()
        host_aggregates = self.model_scope.get("host_aggregates")
        availability_zones = self.model_scope.get("availability_zones")
        if host_aggregates:
            self._collect_aggregates(host_aggregates, compute_nodes)
        if availability_zones:
            self._collect_zones(availability_zones, compute_nodes)

        if not compute_nodes:
            self.no_model_scope_flag = True
            all_nodes = self.nova_helper.get_compute_node_list()
            compute_nodes = set(
                [node.hypervisor_hostname for node in all_nodes])
        LOG.debug("compute nodes: %s", compute_nodes)
        for node_name in compute_nodes:
            cnode = self.nova_helper.get_compute_node_by_name(node_name,
                                                              servers=True,
                                                              detailed=True)
            if cnode:
                node_info = cnode[0]
                self.add_compute_node(node_info)
                # node.servers is a list of server objects
                # New in nova version 2.53
                instances = getattr(node_info, "servers", None)
                self.add_instance_node(node_info, instances)

    def add_compute_node(self, node):
        # Build and add base node.
        LOG.debug("node info: %s", node)
        compute_node = self.build_compute_node(node)
        self.model.add_node(compute_node)

        # NOTE(v-francoise): we can encapsulate capabilities of the node
        # (special instruction sets of CPUs) in the attributes; as well as
        # sub-nodes can be added re-presenting e.g. GPUs/Accelerators etc.

        # # Build & add disk, memory, network and cpu nodes.
        # disk_id, disk_node = self.build_disk_compute_node(base_id, node)
        # self.add_node(disk_id, disk_node)
        # mem_id, mem_node = self.build_memory_compute_node(base_id, node)
        # self.add_node(mem_id, mem_node)
        # net_id, net_node = self._build_network_compute_node(base_id)
        # self.add_node(net_id, net_node)
        # cpu_id, cpu_node = self.build_cpu_compute_node(base_id, node)
        # self.add_node(cpu_id, cpu_node)

        # # Connect the base compute node to the dependent nodes.
        # self.add_edges_from([(base_id, disk_id), (base_id, mem_id),
        #                      (base_id, cpu_id), (base_id, net_id)],
        #                     label="contains")

    def build_compute_node(self, node):
        """Build a compute node from a Nova compute node

        :param node: A node hypervisor instance
        :type node: :py:class:`~novaclient.v2.hypervisors.Hypervisor`
        """
        # build up the compute node.
        node_attributes = {
            "id": node.id,
            "uuid": node.service["host"],
            "hostname": node.hypervisor_hostname,
            "memory": node.memory_mb,
            "disk": node.free_disk_gb,
            "disk_capacity": node.local_gb,
            "vcpus": node.vcpus,
            "state": node.state,
            "status": node.status,
            "disabled_reason": node.service["disabled_reason"]}

        compute_node = element.ComputeNode(**node_attributes)
        # compute_node = self._build_node("physical", "compute", "hypervisor",
        #                                 node_attributes)
        return compute_node

    def add_instance_node(self, node, instances):
        if instances is None:
            # no instances on this node
            return
        host = node.service["host"]
        compute_node = self.model.get_node_by_uuid(host)
        # Get all servers on this compute host.
        instances = self.nova_helper.get_instance_list({'host': host})
        for inst in instances:
            # Add Node
            instance = self._build_instance_node(inst)
            self.model.add_instance(instance)
            # Connect the instance to its compute node
            self.model.map_instance(instance, compute_node)

    def _build_instance_node(self, instance):
        """Build an instance node

        Create an instance node for the graph using nova and the
        `server` nova object.
        :param instance: Nova VM object.
        :return: An instance node for the graph.
        """
        flavor = instance.flavor
        instance_attributes = {
            "uuid": instance.id,
            # TODO(chenker) human_id is deprecated for removal. For the reason,
            # please reference bug 1833665.
            "human_id": instance.human_id,
            "name": instance.name,
            "memory": flavor["ram"],
            "disk": flavor["disk"],
            "disk_capacity": flavor["disk"],
            "vcpus": flavor["vcpus"],
            "state": getattr(instance, "OS-EXT-STS:vm_state"),
            "metadata": instance.metadata,
            "project_id": instance.tenant_id,
            "locked": instance.locked}

        # node_attributes = dict()
        # node_attributes["layer"] = "virtual"
        # node_attributes["category"] = "compute"
        # node_attributes["type"] = "compute"
        # node_attributes["attributes"] = instance_attributes
        return element.Instance(**instance_attributes)

    def _merge_compute_scope(self, compute_scope):
        model_keys = self.model_scope.keys()
        update_flag = False

        role_keys = ("host_aggregates", "availability_zones")
        for role in compute_scope:
            role_key = list(role.keys())[0]
            if role_key not in role_keys:
                continue
            role_values = list(role.values())[0]
            if role_key in model_keys:
                for value in role_values:
                    if value not in self.model_scope[role_key]:
                        self.model_scope[role_key].append(value)
                        update_flag = True
            else:
                self.model_scope[role_key] = role_values
                update_flag = True
        return update_flag

    def _check_model_scope(self, model_scope):
        compute_scope = []
        update_flag = False
        for _scope in model_scope:
            if 'compute' in _scope:
                compute_scope = _scope['compute']
                break

        if self.no_model_scope_flag is False:
            if compute_scope:
                update_flag = self._merge_compute_scope(compute_scope)
            else:
                self.model_scope = dict()
                update_flag = True

        return update_flag

    def execute(self, model_scope):
        """Instantiates the graph with the openstack cluster data.

        The graph is populated along 2 layers: virtual and physical. As each
        new layer is built connections are made back to previous layers.
        """
        updata_model_flag = self._check_model_scope(model_scope)
        if self.model is None or updata_model_flag:
            self.model = self.model or model_root.ModelRoot()
            self._add_physical_layer()

        return self.model
