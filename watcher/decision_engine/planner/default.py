# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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
#

import json

import enum
from oslo_log import log

from watcher._i18n import _LW
from watcher.common import utils
from watcher.decision_engine.planner import base
from watcher import objects

LOG = log.getLogger(__name__)


class Primitives(enum.Enum):
    LIVE_MIGRATE = 'MIGRATE'
    COLD_MIGRATE = 'MIGRATE'
    POWER_STATE = 'POWERSTATE'
    HYPERVISOR_STATE = 'HYPERVISOR_STATE'
    NOP = 'NOP'


class DefaultPlanner(base.BasePlanner):
    priorities = {
        'nop': 0,
        'migrate': 1,
        'change_nova_service_state': 2,
    }

    def create_action(self,
                      action_plan_id,
                      action_type,
                      applies_to,
                      input_parameters=None):
        uuid = utils.generate_uuid()
        action = {
            'uuid': uuid,
            'action_plan_id': int(action_plan_id),
            'action_type': action_type,
            'applies_to': applies_to,
            'input_parameters': json.dumps(input_parameters),
            'state': objects.action.Status.PENDING,
            'alarm': None,
            'next': None,
        }
        return action

    def schedule(self, context, audit_id, solution):
        LOG.debug('Create an action plan for the audit uuid')
        action_plan = self._create_action_plan(context, audit_id)

        actions = list(solution.actions)
        to_schedule = []
        for action in actions:
            json_action = self.create_action(action_plan_id=action_plan.id,
                                             action_type=action.get(
                                                 'action_type'),
                                             applies_to=action.get(
                                                 'applies_to'),
                                             input_parameters=action.get(
                                                 'input_parameters'))
            to_schedule.append((self.priorities[action.get('action_type')],
                                json_action))

        # scheduling
        scheduled = sorted(to_schedule, key=lambda x: (x[0]))
        if len(scheduled) == 0:
            LOG.warning(_LW("The action plan is empty"))
            action_plan.first_action_id = None
            action_plan.save()
        else:
            parent_action = self._create_action(context,
                                                scheduled[0][1],
                                                None)
            scheduled.pop(0)

            action_plan.first_action_id = parent_action.id
            action_plan.save()

            for s_action in scheduled:
                action = self._create_action(context, s_action[1],
                                             parent_action)
                parent_action = action

        return action_plan

    def _create_action_plan(self, context, audit_id):
        action_plan_dict = {
            'uuid': utils.generate_uuid(),
            'audit_id': audit_id,
            'first_action_id': None,
            'state': objects.action_plan.Status.RECOMMENDED
        }

        new_action_plan = objects.ActionPlan(context, **action_plan_dict)
        new_action_plan.create(context)
        new_action_plan.save()
        return new_action_plan

    def _create_action(self, context, _action, parent_action):
        action_description = str(_action)
        LOG.debug("Create a action for the following resquest : %s"
                  % action_description)

        new_action = objects.Action(context, **_action)
        new_action.create(context)
        new_action.save()

        if parent_action:
            parent_action.next = new_action.id
            parent_action.save()

        return new_action
