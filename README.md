# Carla Simulator 

- [Demo](https://github.com/happyOBO/leaderboard#1-데모-영상)
- [Installation & Running](https://github.com/happyOBO/leaderboard#2-설치-및-실행-방법)
- [Code Description](https://github.com/happyOBO/leaderboard#3-코드-설명)

## 1. Demo

[![Video Label](http://img.youtube.com/vi/K5ujXesSI_4/0.jpg)](https://youtu.be/K5ujXesSI_4)

## 2. Installation & Running

1. Basic preferences
    1. Nvidia settings
        - Enter ``System Settings > Software & Updates > Additional Drivers`` tab and click ``Using Nvidia binary driver``.
    2. anaconda setting
        - [anaconda installation](https://www.anaconda.com/products/individual#linux)
        - Install the anaconda version that suits your computer from the site.
2. installation
    1. If you already have ``carla (CARLA 0.9.10.1)`` and ``Scenario_Runner``, please proceed from step 5.
    2. Download the binary **CARLA 0.9.10.1 release**.
        - [CARLA 0.9.10.1](https://carla-releases.s3.eu-west-3.amazonaws.com/Linux/CARLA_0.9.10.1.tar.gz) 

    3. Unzip the package and install some dependencies in new environment to use the CARLA PYTHON API.
        ```bash
        conda create -n py37 python=3.7
        conda activate py37 # or source activate py37 
        cd ${CARLA_ROOT}  # Change ${CARLA_ROOT} for your CARLA root folder
        pip3 install -r PythonAPI/carla/requirements.txt
        easy_install PythonAPI/carla/dist/carla-0.9.10-py3.7-linux-x86_64.egg
        ```
    4. Download the Scenario_Runner Repository and Install the required Python dependencies.
        ```bash
        git clone -b leaderboard --single-branch https://github.com/carla-simulator/scenario_runner.git
        cd ${SCENARIO_RUNNER_ROOT} # Change ${SCENARIO_RUNNER_ROOT} for your Scenario_Runner root folder
        pip3 install -r requirements.txt
        ```
    5. Download the **My Scenario_Runner Repository** and Install the required Python dependencies.
        ```bash
        git clone https://github.com/happyOBO/leaderboard.git
        cd ${LEADERBOARD_ROOT} # Change ${LEADERBOARD_ROOT} for your Leaderboard root folder
        pip3 install -r requirements.txt
        ```
    6. Edit your ``~/.bashrc`` profile, adding the following definitions:
        ```bash
        # .bashrc
        export CARLA_ROOT=PATH_TO_CARLA_ROOT
        export SCENARIO_RUNNER_ROOT=PATH_TO_SCENARIO_RUNNER
        export LEADERBOARD_ROOT=PATH_TO_LEADERBOARD
        export PYTHONPATH="${CARLA_ROOT}/PythonAPI/carla/":"${SCENARIO_RUNNER_ROOT}":"${LEADERBOARD_ROOT}":${PYTHONPATH}
        ```
3.  Running
    1. Activate the created environment on all terminals to use.
        ```bash
        conda activate py37 # or source activate py37
        ```
    2. Run the CARLA server in one terminal. I worked on the assignment with ``-opengl`` added.
        ```bash
        cd ${CARLA_ROOT}
        ./CarlaUE4.sh -quality-level=Epic -opengl -world-port=2000 -resx=800 -resy=600
        ```
    3. Create a Python script that sets some environment variables for parameterization, and runs the ``run_evaluation.sh``. 
        ```bash
        export SCENARIOS=${LEADERBOARD_ROOT}/data/all_towns_traffic_scenarios_public.json
        export ROUTES=${LEADERBOARD_ROOT}/data/routes_devtest.xml
        export REPETITIONS=1
        export DEBUG_CHALLENGE=1
        export TEAM_AGENT=${LEADERBOARD_ROOT}/leaderboard/autoagents/human_agent.py
        export PYTHONPATH="${CARLA_ROOT}/PythonAPI/carla/":"${SCENARIO_RUNNER_ROOT}":"${LEADERBOARD_ROOT}":${PYTHONPATH}
        export CHECKPOINT_ENDPOINT=${LEADERBOARD_ROOT}/results.json
        export CHALLENGE_TRACK_CODENAME=SENSORS

        $LEADERBOARD_ROOT/scripts/run_evaluation.sh
        ```
    4. After execution, a screen similar to the demo video is displayed, and movement can be controlled through the arrow keys or the W, A, S, D keys. You can interrupt the current scenario and move to the next map with ``Ctrl`` + ``C`` keys.

## 3. Code Description
- Implemented by changing the code provided by ``leader_board``. Some of the files that I have implemented are ``${LEADERBOARD_ROOT}/leaderboard/scenarios/scenario_manager.py`` and ``${LEADERBOARD_ROOT}/leaderboard/autoagents/human_agent.py``.
1. The agent shows images taken from one camera sensor on the display every frame.
    - Define ``sensor`` in ``human_agent.py``.
        ```py
        sensors = [
        {'type': 'sensor.camera.rgb', 'x': 0.7, 'y': 0.0, 'z': 1.60, 'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0,
            'width': 800, 'height': 600, 'fov': 100, 'id': 'Center'},
        {'type': 'sensor.speedometer', 'reading_frequency': 20, 'id': 'speed'},
        ]
        ```
    - Set the sensor in ``ego_vehicle`` through ``setup_sensors()`` in ``scenario_manager.py``.
        ```py
        self._agent.setup_sensors(self.ego_vehicles[0], self._debug_mode)
        ```
    - Accumulate sensor values ​​through ``update_sensor()`` in ``sensor_interface.py``
        ```py
        self._data_provider.update_sensor(tag, array, image.frame)
        ```
    - Import data from ``autonomous_agent.py`` through ``self.sensor_interface.get_data()``.
        ```py
        input_data = self.sensor_interface.get_data()
        ```
    - From ``human_agent.py``, through ``pygame``, it shows the data value with ``id`` as ``Center`` on the display.
        ```py
        image_center = input_data['Center'][1][:, :, -2::-1]
        self._surface = pygame.surfarray.make_surface(image_center.swapaxes(0, 1))
        self._display.blit(self._surface, (0, 0))
        ```
2. The agent draws the bounding boxes of all vehicles and walkers located within a 50m radius of the ego vehicle overlaid on the image taken from the camera sensor.
    - Import data all about ``vehicle actor`` from ``scenario_manager.py`` through ``world.get_actors().filter('vehicle.*')``.
    - If the distance from the ``location`` of the ``vehicle`` to the ``location`` of the ``ego_vehicle`` is within 50m, draw a box through ``draw_box``.
        ```py
        for vehicle in world.get_actors().filter('vehicle.*'):
            vehicle_location = vehicle.get_location()
            if(ego_vehicle.id != vehicle.id and vehicle.is_alive): # ego_vehicle 이 아니고, 살아있는 vehicle 에 대해서만 박스를 그린다.
                if((ego_location.x -vehicle_location.x)**2 + (ego_location.y - vehicle_location.y)**2  < 2500): # 거리의 제곱이 50^2 이내일때
                    
                    # draw Box
                    transform = vehicle.get_transform()
                    bounding_box = vehicle.bounding_box
                    bounding_box.location += transform.location
                    world.debug.draw_box(bounding_box, transform.rotation, thickness = 0.1, color = carla.Color(10,15,219,0), life_time=0.006) # vehicles are blue box!
                            
        ```
    - ``walker`` also performs the same process.
4. The agent receives keyboard input and controls the steer, throttle, and brake of the ego vehicle.
    - Control of ``vehicle`` is received through ``get_control()`` and applied through ``apply_control()``.
    - Get the keyboard value from ``human_agent.py`` through ``pygame.key.get_pressed()``, and change the value according to the keyboard value.
        ```py
            if keys[K_UP] or keys[K_w]:
                self._control.throttle = 0.6
            else:
                self._control.throttle = 0.0

            steer_increment = 3e-4 * milliseconds
            if keys[K_LEFT] or keys[K_a]:
                self._steer_cache -= steer_increment
            elif keys[K_RIGHT] or keys[K_d]:
                self._steer_cache += steer_increment
            else:
                self._steer_cache = 0.0
        ```

5. The agent maintains the brake value at 1.0 when another actor (Vehicle, Walker) exists within 0m ~ 10m in front of the ego vehicle and -3m ~ 3m in the left and right.
    - Use ``location'' and ``rotation'' of ``ego_vehicle'' to designate the front, left and right areas. With ``rotation.yaw'' you can find a point that is the desired ``distance'' in that direction.
        ```py
        # each angles 0, -90, 90 are front left right arrow. 
        interval_point.x = ego_location.x + distance * cos(radians(yaw + angle))
        interval_point.y = ego_location.y + distance * sin(radians(yaw + angle))
        ```
    - You can get points ``left_symmetry'' and ``right_symmetry'' that are width apart from ``interval_point'' based on the direction of the vehicle.
        ```py
        # slope is tan(radians(yaw + angle))
        left_symmetry.x = - width * slope * math.sqrt(1/ (slope **2 + 1)) + interval_point.x 
        left_symmetry.y = width * math.sqrt( 1 / (slope **2 + 1)) + interval_point.y
        right_symmetry.x = width * slope * math.sqrt( 1 / (slope **2 + 1)) + interval_point.x 
        right_symmetry.y = - width * math.sqrt(1  / (slope**2 + 1)) + interval_point.y
        ```
    - As shown in the picture (a) below, two normals passing through ``interval_point`` and ``ego_location`` respectively, and two parallel lines passing through ``left_symmetry`` and ``right_symmetry`` based on the direction of ``ego_vehicle`` Can be seen.
    - As shown in the photo (b) below, the ``location.x`` value of the ``vehicle / walker`` currently being searched is substituted for the straight lines facing each other, and the ``location.x`` of the ``vehicle / walker``. If the product minus y`` is negative, it can be said that there is a ``vehicle / walker`` between the two straight lines.

        <img src="./asset/set_area.png" width="800">
    - When the product is negative, change the ``brake`` value to ``1.0``.
        ```py
        front_diff = (vehicle_location.x - interval_point.x) / slope + interval_point[i].y - vehicle_location.y
        back_diff = (vehicle_location.x - ego_location.x) / slope + ego_location.y - vehicle_location.y
        left_diff = (vehicle_location.x - left_symmetry.x ) * slope[i] + left_symmetry.y - vehicle_location.y
        right_diff = (vehicle_location.x - right_symmetry.x) * slope[i] + right_symmetry.y - vehicle_location.y
        if(front_diff * back_diff < 0 and left_diff * right_diff < 0):
            control.brake = 1.0
        ```
6. The agent counts CollisionEvents between the ego vehicle and other actors (Vehicle, Walker) and shows the number of collisions on the display as a score.
    - The agent counts CollisionEvents between the ego vehicle and other actors (Vehicle, Walker) and shows the number of collisions on the display as a score.
    - Items that are good to appear on the display are stored in ``display_additional_info``
    - ``display_additional_info``: ``steer``, ``throttle``, ``brake`` of ``ego_vehicle``, number of collisions, ``type_id`` of ``actor`` located in the front, left and right areas
    - Show the corresponding values ​​on the display through ``pygame`` in ``human_agent.py``.