# -*- encoding: utf-8 -*-
# Copyright (c) 2019 European Organization for Nuclear Research (CERN)
#
# Authors: Corne Lukken <info@dantalion.nl>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_config import cfg

grafana_client = cfg.OptGroup(name='grafana_client',
                              title='Configuration Options for Grafana')

GRAFANA_CLIENT_OPTS = [
    # TODO(Dantali0n) each individual metric could have its own token.
    # A similar structure to the database_map would solve this.
    cfg.StrOpt('token',
               default=None,
               help="Authentication token to gain access"),
    # TODO(Dantali0n) each individual metric could have its own base url.
    # A similar structure to the database_map would solve this.
    cfg.StrOpt('base_url',
               default=None,
               help="first part of the url (including https:// or http://) up "
                    "until project id part. "
                    "Example: https://secure.org/api/datasource/proxy/"),
    cfg.DictOpt('project_id_map',
                default={
                    'host_cpu_usage': None,
                    'host_ram_usage': None,
                    'host_outlet_temp': None,
                    'host_inlet_temp': None,
                    'host_airflow': None,
                    'host_power': None,
                    'instance_cpu_usage': None,
                    'instance_ram_usage': None,
                    'instance_ram_allocated': None,
                    'instance_l3_cache_usage': None,
                    'instance_root_disk_size': None,
                },
                help="Mapping of grafana project ids to datasource metrics. "
                     "Dictionary values should be positive integers. "
                     "Example: 7465"),
    cfg.DictOpt('database_map',
                default={
                    'host_cpu_usage': None,
                    'host_ram_usage': None,
                    'host_outlet_temp': None,
                    'host_inlet_temp': None,
                    'host_airflow': None,
                    'host_power': None,
                    'instance_cpu_usage': None,
                    'instance_ram_usage': None,
                    'instance_ram_allocated': None,
                    'instance_l3_cache_usage': None,
                    'instance_root_disk_size': None,
                },
                help="Mapping of grafana databases to datasource metrics. "
                     "Values should be strings. Example: influx_production"),
    cfg.DictOpt('attribute_map',
                default={
                    'host_cpu_usage': None,
                    'host_ram_usage': None,
                    'host_outlet_temp': None,
                    'host_inlet_temp': None,
                    'host_airflow': None,
                    'host_power': None,
                    'instance_cpu_usage': None,
                    'instance_ram_usage': None,
                    'instance_ram_allocated': None,
                    'instance_l3_cache_usage': None,
                    'instance_root_disk_size': None,
                },
                help="Mapping of resource attributes to datasource metrics. "
                     "For a complete list of available attributes see "
                     "instance.py and node.py in "
                     "decision_engine/model/element. "
                     "Values should be strings. Example: hostname"),
    cfg.DictOpt('translator_map',
                default={
                    'host_cpu_usage': None,
                    'host_ram_usage': None,
                    'host_outlet_temp': None,
                    'host_inlet_temp': None,
                    'host_airflow': None,
                    'host_power': None,
                    'instance_cpu_usage': None,
                    'instance_ram_usage': None,
                    'instance_ram_allocated': None,
                    'instance_l3_cache_usage': None,
                    'instance_root_disk_size': None,
                },
                help="Mapping of grafana translators to datasource metrics. "
                     "Values should be strings. Example: influxdb"),
    cfg.DictOpt('query_map',
                # {0} = aggregate
                # {1} = attribute
                # {2} = period
                # {3} = granularity
                # {4} = { influxdb: retention_period, }
                default={
                    'host_cpu_usage': None,
                    'host_ram_usage': None,
                    'host_outlet_temp': None,
                    'host_inlet_temp': None,
                    'host_airflow': None,
                    'host_power': None,
                    'instance_cpu_usage': None,
                    'instance_ram_usage': None,
                    'instance_ram_allocated': None,
                    'instance_l3_cache_usage': None,
                    'instance_root_disk_size': None,
                },
                help="Mapping of grafana queries to datasource metrics. "
                     "Values should be strings for which the .format method "
                     "will transform it. These queries will need to be "
                     "constructed using tools such as Postman. "
                     "Example: SELECT cpu FROM {4}.cpu_percent WHERE "
                     "host == '{1}' AND time > now()-{2}s")]


def register_opts(conf):
    conf.register_group(grafana_client)
    conf.register_opts(GRAFANA_CLIENT_OPTS, group=grafana_client)


def list_opts():
    return [('grafana_client', GRAFANA_CLIENT_OPTS)]
