# Carla 

- [데모 영상]()
- [설치 및 실행방법]()
- [코드 설명]()

## 1. 데모 영상

## 2. 설치 및 실행 방법
- 추가할 내용, 우분투 그 nvidia 설정한다.
1. 기본 환경 설정
    1. Nvidia 설정
        - ``System Settings > Software & Updates > Additional Drivers`` 탭에 들어가서 ``Using Nvidia binary driver`` 를 클릭합니다
    2. anaconda 설치
        - [anaconda 사이트](https://www.anaconda.com/products/individual#linux)에서 자신에게 맞게 설치합니다.
2. 설치
    1. 바이너리 파일 [CARLA 0.9.10.1](https://carla-releases.s3.eu-west-3.amazonaws.com/Linux/CARLA_0.9.10.1.tar.gz)을 다운로드 받습니다. 

    2. 압축 파일을 풀고, CARLA PYTHON API를 사용하기 위해 몇가지 종속성을 설치합니다.
        ```bash
        conda create -n py37 python=3.7
        conda activate py37 # 아나콘다 예전 버전은 source activate py37 
        cd ${CARLA_ROOT}  # Change ${CARLA_ROOT} for your CARLA root folder
        pip3 install -r PythonAPI/carla/requirements.txt
        easy_install PythonAPI/carla/dist/carla-0.9.10-py3.7-linux-x86_64.egg
        ```
    2. 제가 변경한 ``leader_board`` 코드들을 다운 받고 ``python`` 종속성을 설치합니다.
        ```bash
        git clone https://github.com/happyOBO/Carla
        cd ${LEADERBOARD_ROOT} # Change ${LEADERBOARD_ROOT} for your Leaderboard root folder
        pip3 install -r requirements.txt
        ```
    3. Scenario_Runner 레포지토리도 다운받고, 종속성을 설치합니다.
        ```bash
        git clone -b leaderboard --single-branch https://github.com/carla-simulator/scenario_runner.git
        cd ${SCENARIO_RUNNER_ROOT} # Change ${SCENARIO_RUNNER_ROOT} for your Scenario_Runner root folder
        pip3 install -r requirements.txt
        ```
    4. ``~/.bashrc`` 파일에 아래와 같이 환경변수를 추가합니다.
        ```bash
        # .bashrc
        export CARLA_ROOT=PATH_TO_CARLA_ROOT
        export SCENARIO_RUNNER_ROOT=PATH_TO_SCENARIO_RUNNER
        export LEADERBOARD_ROOT=PATH_TO_LEADERBOARD
        export PYTHONPATH="${CARLA_ROOT}/PythonAPI/carla/":"${SCENARIO_RUNNER_ROOT}":"${LEADERBOARD_ROOT}":${PYTHONPATH}
        ```
3.  실행
    1. 사용할 모든 터미널에 이전에 만들었던 가상환경을 활성화 시킵니다.
        ```bash
        conda activate py37 # 또는 source activate py37
        ```
    2. 한 터미널에 CARLA 서버를 실행시킵니다. 저는 ``-opengl``을 추가한 상태에서 과제를 진행했습니다.
        ```bash
        cd ${CARLA_ROOT}
        ./CarlaUE4.sh -quality-level=Epic -opengl -world-port=2000 -resx=800 -resy=600
        ```
    3. 다른 한 터미널에는 환경변수를 추가해주고, ``run_evalution.sh``를 실행시킵니다.
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