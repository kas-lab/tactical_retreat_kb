# typedb_tactics

## Models

### Dependencies

```mermaid
graph LR
    data_structure["data_structure.tql"]
    context["context_model.tql"]
    ros["ros_model.tql"]
    feature["feature_model.tql"]
    tactics["tactics_model.tql"]
    discover["discover_tactics_model.tql"]

    data_structure --> context
    context --> ros
    ros --> tactics
    feature --> tactics
    tactics --> discover
```

Arrows point from each prerequisite model to the model that depends on it.


## Docker

### Build

```Bash
docker build -t rebet .
```

### Run

```Bash
xhost +
```

Start container in the background with typedb server running:

```Bash
docker run -d --rm --name rebet -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 -v /tmp/.X11-unix:/tmp/.X11-unix -v /etc/localtime:/etc/localtime:ro -v $HOME/rebet_ws/src/typedb_tactics:/home/ubuntu-user/rebet_ws/src/typedb_tactics rebet typedb server
```

```Bash
docker run -d --rm --name rebet -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 -v /tmp/.X11-unix:/tmp/.X11-unix -v /etc/localtime:/etc/localtime:ro -v $HOME/ros_workspaces/rebet_ws/src/typedb_tactics:/home/ubuntu-user/rebet_ws/src/typedb_tactics rebet typedb server
```

```Bash
docker run -d --rm --name rebet --runtime=nvidia --gpus all -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 -v /tmp/.X11-unix:/tmp/.X11-unix -v /etc/localtime:/etc/localtime:ro -v $HOME/ros_workspaces/rebet_ws/src/typedb_tactics:/home/ubuntu-user/rebet_ws/src/typedb_tactics rebet typedb server
```

```Bash
docker run -d --rm --name rebet --runtime=nvidia --gpus all -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 -v /tmp/.X11-unix:/tmp/.X11-unix -v /etc/localtime:/etc/localtime:ro -v $HOME/ros_workspaces/rebet_ws/src/typedb_tactics:/home/ubuntu-user/rebet_ws/src/typedb_tactics -v $HOME/ros_workspaces/rebet_ws/src/ros_monitors:/home/ubuntu-user/rebet_ws/src/ros_monitors rebet typedb server
```

Start new terminal in the container:

```Bash
docker exec -it rebet bash
```

### Test

```Bash
colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics
```
