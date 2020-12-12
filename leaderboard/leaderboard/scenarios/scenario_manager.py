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
            brake_on = False

            if world:

                # get ego vehicle info
                ego_vehicle = self.ego_vehicles[0]
                control = ego_vehicle.get_control()
                ego_location = ego_vehicle.get_location()

                # initialize area info
                angle = { "front" : 0, "left" : -90.0 , "right" : 90.0 }
                distance = {"front" : 10.0, "left" : 3.0, "right" : 3.0}
                width = {"front" : ego_vehicle.bounding_box.extent.x ,  "left" : ego_vehicle.bounding_box.extent.y * 2, "right" : ego_vehicle.bounding_box.extent.y *2}
                
                yaw = ego_vehicle.get_transform().rotation.yaw
                interval_point = {}
                right_symmetry = {}
                left_symmetry = {}
                slope = {}
                close_actors = []
                
                for i in angle.keys():
                    slope[i] = math.tan(math.radians(yaw + angle[i]))
                    interval_point[i] = carla.Location(ego_location.x + distance[i] * math.cos(math.radians(yaw + angle[i])) , ego_location.y + distance[i] * math.sin(math.radians(yaw + angle[i])) ,0.0)
                    left_symmetry[i] = carla.Location(- width[i] * slope[i] * math.sqrt(1/ (slope[i] **2 + 1)) + interval_point[i].x , width[i] * math.sqrt( 1 / (slope[i] **2 + 1)) + interval_point[i].y ,1.0)
                    right_symmetry[i] = carla.Location( width[i] * slope[i] * math.sqrt( 1 / (slope[i] **2 + 1)) + interval_point[i].x ,- width[i] * math.sqrt(1  / (slope[i]**2 + 1)) + interval_point[i].y ,1.0)
                    
                    # draw Area
                    world.debug.draw_string( interval_point[i],"M", draw_shadow=False, color=carla.Color(225,0,0), life_time= 0.006)
                    world.debug.draw_string( left_symmetry[i],"L", draw_shadow=False, color=carla.Color(225,0,0), life_time= 0.006)
                    world.debug.draw_string( right_symmetry[i],"R", draw_shadow=False, color=carla.Color(225,0,0), life_time= 0.006)
                
                for vehicle in world.get_actors().filter('vehicle.*'):
                    if(ego_vehicle.id != vehicle.id and vehicle.is_alive):
                        if((ego_vehicle.get_location().x - vehicle.get_location().x)**2 + (ego_vehicle.get_location().y - vehicle.get_location().y)**2  < 2500):
                            
                            # draw Box
                            transform = vehicle.get_transform()
                            bounding_box = vehicle.bounding_box
                            bounding_box.location += transform.location
                            world.debug.draw_box(bounding_box, transform.rotation, thickness = 0.07, color = carla.Color(10,15,219,0), life_time=0.006)
                            
                            # Front, left, right area check 
                            vehicle_location = vehicle.get_location()
                            for i in angle.keys():
                                front_diff = (vehicle_location.x - interval_point[i].x) / slope[i] + interval_point[i].y - vehicle_location.y
                                back_diff = (vehicle_location.x - ego_location.x) / slope[i] + ego_location.y - vehicle_location.y
                                left_diff = (vehicle_location.x - left_symmetry[i].x ) * slope[i] + left_symmetry[i].y - vehicle_location.y
                                right_diff = (vehicle_location.x - right_symmetry[i].x) * slope[i] + right_symmetry[i].y - vehicle_location.y
                                if(front_diff * back_diff < 0 and left_diff * right_diff < 0):
                                    brake_on = True
                                    close_actors.append(vehicle.type_id)

                for walker in world.get_actors().filter('walker.*'):
                    if(ego_vehicle.id != walker.id and walker.is_alive):
                        if((ego_vehicle.get_location().x - walker.get_location().x)**2 + (ego_vehicle.get_location().y - walker.get_location().y)**2  < 2500):
                            
                            # draw Box
                            transform = walker.get_transform()
                            bounding_box = walker.bounding_box
                            bounding_box.location += transform.location
                            world.debug.draw_box(bounding_box, transform.rotation, thickness = 0.07, color = carla.Color(215,10,15,0), life_time=0.006)

                            # Front, left, right area check
                            walker_location = walker.get_location()
                            for i in angle.keys():
                                front_diff = (walker_location.x - interval_point[i].x) / slope[i] + interval_point[i].y - walker_location.y
                                back_diff = (walker_location.x - ego_location.x) / slope[i] + ego_location.y - walker_location.y
                                left_diff = (walker_location.x - left_symmetry[i].x ) * slope[i] + left_symmetry[i].y - walker_location.y
                                right_diff = (walker_location.x - right_symmetry[i].x) * slope[i] + right_symmetry[i].y - walker_location.y
                                if(front_diff * back_diff < 0 and left_diff * right_diff < 0):
                                    brake_on = True
                                    close_actors.append(walker.type_id)

                snapshot = world.get_snapshot()
                if snapshot:
                    timestamp = snapshot.timestamp
            if timestamp:
                self._tick_scenario(timestamp,close_actors, brake_on)



    def _tick_scenario(self, timestamp , close_actors = None ,brake_on = False):
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
            control = self.ego_vehicles[0].get_control()

            display_additional_info = {"throttle" : control.throttle, "steer" : control.steer, "brake" : control.brake , "collision" : coll_value , "actors" : close_actors}
            
            try:
                ego_action = self._agent.agent_call(display_additional_info) # print tick count # display 

            # Special exception inside the agent that isn't caused by the agent
            except SensorReceivedNoData as e:
                raise RuntimeError(e)

            except Exception as e:
                raise AgentError(e)
            ego_action.brake = 1 if brake_on else ego_action.brake
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
