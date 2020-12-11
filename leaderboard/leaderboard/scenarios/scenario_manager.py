#!/usr/bin/env python

# Copyright (c) 2018-2020 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

"""
This module provides the ScenarioManager implementations.
It must not be modified and is for reference only!
"""

from __future__ import print_function
import signal
import sys
import time

import py_trees
import carla

import math

from srunner.scenariomanager.carla_data_provider import CarlaDataProvider
from srunner.scenariomanager.timer import GameTime
from srunner.scenariomanager.watchdog import Watchdog

from leaderboard.autoagents.agent_wrapper import AgentWrapper, AgentError
from leaderboard.envs.sensor_interface import SensorReceivedNoData
from leaderboard.utils.result_writer import ResultOutputProvider # testing result -> fail or Succes


class ScenarioManager(object):

    """
    Basic scenario manager class. This class holds all functionality
    required to start, run and stop a scenario.

    The user must not modify this class.

    To use the ScenarioManager:
    1. Create an object via manager = ScenarioManager()
    2. Load a scenario via manager.load_scenario()
    3. Trigger the execution of the scenario manager.run_scenario()
       This function is designed to explicitly control start and end of
       the scenario execution
    4. If needed, cleanup with manager.stop_scenario()
    """


    def __init__(self, timeout, debug_mode=False):
        """
        Setups up the parameters, which will be filled at load_scenario()
        """
        self.scenario = None
        self.scenario_tree = None
        self.scenario_class = None
        self.ego_vehicles = None
        self.other_actors = None

        self._debug_mode = debug_mode
        self._agent = None
        self._running = False
        self._timestamp_last_run = 0.0
        self._timeout = float(timeout)

        # Used to detect if the simulation is down
        watchdog_timeout = max(5, self._timeout - 2)
        self._watchdog = Watchdog(watchdog_timeout)

        # Avoid the agent from freezing the simulation
        agent_timeout = watchdog_timeout - 1
        self._agent_watchdog = Watchdog(agent_timeout)

        self.scenario_duration_system = 0.0
        self.scenario_duration_game = 0.0
        self.start_system_time = None
        self.end_system_time = None
        self.end_game_time = None


        # Register the scenario tick as callback for the CARLA world
        # Use the callback_id inside the signal handler to allow external interrupts
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        """
        Terminate scenario ticking when receiving a signal interrupt
        """
        self._running = False

    def cleanup(self):
        """
        Reset all parameters
        """
        self._timestamp_last_run = 0.0
        self.scenario_duration_system = 0.0
        self.scenario_duration_game = 0.0
        self.start_system_time = None
        self.end_system_time = None
        self.end_game_time = None

    def load_scenario(self, scenario, agent, rep_number):
        """
        Load a new scenario
        """

        GameTime.restart()
        self._agent = AgentWrapper(agent)
        self.scenario_class = scenario
        self.scenario = scenario.scenario
        self.scenario_tree = self.scenario.scenario_tree
        self.ego_vehicles = scenario.ego_vehicles
        self.other_actors = scenario.other_actors
        self.repetition_number = rep_number

        # To print the scenario tree uncomment the next line
        # py_trees.display.render_dot_tree(self.scenario_tree)

        self._agent.setup_sensors(self.ego_vehicles[0], self._debug_mode)

    def run_scenario(self,args):
        """
        Trigger the start of the scenario and wait for it to finish/fail
        """
        self.start_system_time = time.time()
        self.start_game_time = GameTime.get_time()

        self._watchdog.start()
        self._running = True

        while self._running:
            timestamp = None
            world = CarlaDataProvider.get_world()

            if world:
                ego_vehicle = self.ego_vehicles[0] 
                for vehicle in world.get_actors().filter('vehicle.*'):
                    # draw Box 
                    if(ego_vehicle.id != vehicle.id and vehicle.is_alive):
                        if((ego_vehicle.get_location().x - vehicle.get_location().x)**2 + (ego_vehicle.get_location().y - vehicle.get_location().y)**2  < 2500):
                            transform = vehicle.get_transform()
                            bounding_box = vehicle.bounding_box
                            bounding_box.location += transform.location
                            # print(ego_vehicle.get_transform().rotation , ego_vehicle.get_transform().location)
                            world.debug.draw_box(bounding_box, transform.rotation, thickness = 0.07, color = carla.Color(10,15,219,0), life_time=0.006)


                            # check front 10m
                            yaw = ego_vehicle.get_transform().rotation.yaw
                            interval_front_point = carla.Location(ego_vehicle.get_location().x + 10.0 * math.cos(math.radians(yaw)) , ego_vehicle.get_location().y + 10.0 * math.sin(math.radians(yaw)) ,0.0)
                            interval_left_point = carla.Location(ego_vehicle.get_location().x + 3.0 * math.cos(math.radians(yaw - 90.0)) , ego_vehicle.get_location().y + 3.0 * math.sin(math.radians(yaw- 90.0)) ,0.0)
                            interval_right_point = carla.Location(ego_vehicle.get_location().x + 3.0 * math.cos(math.radians(yaw + 90.0)) , ego_vehicle.get_location().y + 3.0 * math.sin(math.radians(yaw + 90.0)) ,0.0)
                            # 기울기


                            # 전방

                            x_c = interval_front_point.x
                            y_c = interval_front_point.y
                            x_0 = ego_vehicle.get_location().x
                            y_0 = ego_vehicle.get_location().y
                            interval_rect = []
                            front_diff = (vehicle.get_location().x - x_c) / math.tan(math.radians(yaw)) + y_c - vehicle.get_location().y
                            back_diff =  (vehicle.get_location().x - x_0) / math.tan(math.radians(yaw)) + y_0 - vehicle.get_location().y
                            front_l_p = carla.Location(- 2 *math.tan(math.radians(yaw)) * math.sqrt(1/ (math.tan(math.radians(yaw))**2 + 1)) + x_c, math.sqrt(4/ (math.tan(math.radians(yaw))**2 + 1)) + y_c ,0.0)
                            front_r_p = carla.Location(  2 *math.tan(math.radians(yaw)) * math.sqrt( 1 / (math.tan(math.radians(yaw))**2 + 1)) + x_c,- math.sqrt(4 / (math.tan(math.radians(yaw))**2 + 1)) + y_c ,0.0)
                            left_diff = (vehicle.get_location().x - front_l_p.x) * math.tan(math.radians(yaw)) + front_l_p.y - vehicle.get_location().y
                            right_diff = (vehicle.get_location().x - front_r_p.x) * math.tan(math.radians(yaw)) + front_r_p.y - vehicle.get_location().y
                            

                            # 왼쪽 방
                            left_x_c = interval_left_point.x
                            left_y_c = interval_left_point.y
                            left_left_diff = (vehicle.get_location().x - left_x_c) / math.tan(math.radians(yaw - 90.0)) + left_y_c - vehicle.get_location().y
                            left_right_diff = (vehicle.get_location().x - x_0) / math.tan(math.radians(yaw - 90.0)) + y_0 - vehicle.get_location().y
                            left_front_l_p =  carla.Location(- 2.4 *math.tan(math.radians(yaw-90.0)) * math.sqrt(1/ (math.tan(math.radians(yaw-90.0))**2 + 1)) + left_x_c, math.sqrt(6/ (math.tan(math.radians(yaw-90.0))**2 + 1)) + left_y_c ,0.0)
                            left_front_r_p = carla.Location( 2.4 *math.tan(math.radians(yaw-90.0)) * math.sqrt(1/ (math.tan(math.radians(yaw-90.0))**2 + 1)) + left_x_c, math.sqrt(6/ (math.tan(math.radians(yaw-90.0))**2 + 1)) + left_y_c ,0.0)
                            left_front_diff = (vehicle.get_location().x - left_front_l_p.x) * math.tan(math.radians(yaw - 90.0)) + left_front_l_p.y - vehicle.get_location().y
                            left_back_diff =(vehicle.get_location().x - left_front_r_p.x) * math.tan(math.radians(yaw - 90.0)) + left_front_r_p.y - vehicle.get_location().y

                            # 오른쪽 방

                            right_x_c = interval_right_point.x
                            right_y_c = interval_right_point.y
                            right_right_diff = (vehicle.get_location().x - right_x_c) / math.tan(math.radians(yaw + 90.0)) + right_y_c - vehicle.get_location().y
                            right_left_diff = (vehicle.get_location().x - x_0) / math.tan(math.radians(yaw + 90.0)) + y_0 - vehicle.get_location().y
                            right_front_l_p =  carla.Location(- 2.4 *math.tan(math.radians(yaw + 90.0)) * math.sqrt(1/ (math.tan(math.radians(yaw+90.0))**2 + 1)) + right_x_c, math.sqrt(6/ (math.tan(math.radians(yaw+90.0))**2 + 1)) + right_y_c ,0.0)
                            right_front_r_p = carla.Location( 2.4 *math.tan(math.radians(yaw+90.0)) * math.sqrt(1/ (math.tan(math.radians(yaw+90.0))**2 + 1)) + right_x_c, math.sqrt(6/ (math.tan(math.radians(yaw+90.0))**2 + 1)) + right_y_c ,0.0)
                            right_front_diff = (vehicle.get_location().x - right_front_l_p.x) * math.tan(math.radians(yaw + 90.0)) + right_front_l_p.y - vehicle.get_location().y
                            right_back_diff =(vehicle.get_location().x - right_front_r_p.x) * math.tan(math.radians(yaw + 90.0)) + right_front_r_p.y - vehicle.get_location().y



                            if(left_diff * right_diff < 0 and back_diff * front_diff < 0):
                                print("brake!!!")
                            elif(left_left_diff * left_right_diff < 0 and left_back_diff * left_front_diff < 0):
                                print("brake!!!!!")
                            elif(right_left_diff * right_right_diff < 0 and right_back_diff * right_front_diff < 0):
                                print("brake!!!!!!")
                            # interval_rect.append(carla.Location(- 3*math.tan(math.radians(yaw)) * math.sqrt(1/ (math.tan(math.radians(yaw))**2 + 1)) + x_c, math.sqrt(9/ (math.tan(math.radians(yaw))**2 + 1)) + y_c ,0.0))
                            # interval_rect.append(carla.Location( 3*math.tan(math.radians(yaw)) *math.sqrt(1/ (math.tan(math.radians(yaw))**2 + 1)) + x_c,- math.sqrt(9 / (math.tan(math.radians(yaw))**2 + 1)) + y_c ,0.0))
                            # interval_rect.append(carla.Location(-3*math.tan(math.radians(yaw)) * math.sqrt(1/ (math.tan(math.radians(yaw))**2 + 1)) + x_0, math.sqrt(9 / (math.tan(math.radians(yaw))**2 + 1)) + y_0 ,0.0))
                            # interval_rect.append(carla.Location( 3*math.tan(math.radians(yaw)) *math.sqrt(1/ (math.tan(math.radians(yaw))**2 + 1)) + x_0,- math.sqrt(9/ (math.tan(math.radians(yaw))**2 + 1)) + y_0 ,0.0))
                            # print("m", (interval_rect[0].y - interval_rect[1].y) / (interval_rect[0].x - interval_rect[1].x)  * math.tan(math.radians(yaw)))

                            # for i in range(4):
                            #     world.debug.draw_string( interval_rect[i] + carla.Location(z=3.0),"H", draw_shadow=False, color=carla.Color(255,i*40,0), life_time=-1.0)
                            world.debug.draw_string( interval_left_point + carla.Location(z=3.0),"H", draw_shadow=False, color=carla.Color(5,40,220), life_time=-1.0)
                            # world.debug.draw_string( ego_vehicle.get_location() + carla.Location(z=3.0),"H", draw_shadow=False, color=carla.Color(5,220,0), life_time=-1.0)
                for walker in world.get_actors().filter('walker.*'):
                    # draw Box 
                    if(ego_vehicle.id != walker.id and walker.is_alive):
                        if((ego_vehicle.get_location().x - walker.get_location().x)**2 + (ego_vehicle.get_location().y - walker.get_location().y)**2  < 2500):
                            transform = walker.get_transform()
                            bounding_box = walker.bounding_box
                            bounding_box.location += transform.location
                            world.debug.draw_box(bounding_box, transform.rotation, thickness = 0.07, color = carla.Color(215,10,15,0), life_time=0.006)
                

                snapshot = world.get_snapshot()
                if snapshot:
                    timestamp = snapshot.timestamp
            if timestamp:
                self._tick_scenario(timestamp)



    def _tick_scenario(self, timestamp):
        """
        Run next tick of scenario and the agent and tick the world.
        """

        if self._timestamp_last_run < timestamp.elapsed_seconds and self._running:
            self._timestamp_last_run = timestamp.elapsed_seconds
            self._watchdog.update()

            # Update game time and actor information
            GameTime.on_carla_tick(timestamp)

            CarlaDataProvider.on_carla_tick()

            coll_value = list(filter(lambda x: x.name == "CollisionTest", self.scenario.get_criteria()))
            coll_value = coll_value[0].actual_value
            try:
                ego_action = self._agent.agent_call(coll_value) # print tick count # display 

            # Special exception inside the agent that isn't caused by the agent
            except SensorReceivedNoData as e:
                raise RuntimeError(e)

            except Exception as e:
                raise AgentError(e)
            self.ego_vehicles[0].apply_control(ego_action)
            # Tick scenario
            self.scenario_tree.tick_once()
            
            if self._debug_mode:
                print("\n")
                py_trees.display.print_ascii_tree(
                    self.scenario_tree, show_status=True)
                sys.stdout.flush()

            if self.scenario_tree.status != py_trees.common.Status.RUNNING:
                self._running = False

            spectator = CarlaDataProvider.get_world().get_spectator()
            ego_trans = self.ego_vehicles[0].get_transform()
            spectator.set_transform(carla.Transform(ego_trans.location + carla.Location(z=50),
                                                        carla.Rotation(pitch=-90)))
            

        if self._running and self.get_running_status():
            CarlaDataProvider.get_world().tick(self._timeout)

    def get_running_status(self):
        """
        returns:
           bool: False if watchdog exception occured, True otherwise
        """
        return self._watchdog.get_status()

    def stop_scenario(self):
        """
        This function triggers a proper termination of a scenario
        """
        self._watchdog.stop()

        self.end_system_time = time.time()
        self.end_game_time = GameTime.get_time()

        self.scenario_duration_system = self.end_system_time - self.start_system_time
        self.scenario_duration_game = self.end_game_time - self.start_game_time

        if self.get_running_status():
            if self.scenario is not None:
                self.scenario.terminate()

            if self._agent is not None:
                self._agent.cleanup()
                self._agent = None

            self.analyze_scenario()

    def analyze_scenario(self):
        """
        Analyzes and prints the results of the route
        """
        global_result = '\033[92m'+'SUCCESS'+'\033[0m'

        for criterion in self.scenario.get_criteria():
            if criterion.test_status != "SUCCESS":
                global_result = '\033[91m'+'FAILURE'+'\033[0m'

        if self.scenario.timeout_node.timeout:
            global_result = '\033[91m'+'FAILURE'+'\033[0m'

        ResultOutputProvider(self, global_result)
