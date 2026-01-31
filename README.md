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

### Pull

You can get the latest docker image with:

```Bash
docker pull ghcr.io/kas-lab/typedb_tactics:latest
```

### Build

To build the img you need to create a github personal access token to read access to private repos, then log in to gh with gh cli

```Bash
gh auth login         # if not logged in
```

Build:

```Bash
docker build --secret id=gh_token,src=<(gh auth token) --build-arg DEPS_CACHE_BUSTER=${date} -t tactical_retreat .
```

### Run

```Bash
xhost +
```

Start container in the background with typedb server running:

```Bash
docker run -d --rm --name tactical_retreat -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 -v /tmp/.X11-unix:/tmp/.X11-unix -v /etc/localtime:/etc/localtime:ro -v $HOME/tactical_retreat_ws/src/typedb_tactics:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics tactical_retreat typedb server
```

```Bash
docker run -d --rm --name tactical_retreat -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 -v /tmp/.X11-unix:/tmp/.X11-unix -v /etc/localtime:/etc/localtime:ro -v $HOME/ros_workspaces/tactical_retreat_ws/src/typedb_tactics:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics tactical_retreat typedb server
```

With nvidia

```Bash
docker run -d --rm --name tactical_retreat --runtime=nvidia --gpus all -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 -v /tmp/.X11-unix:/tmp/.X11-unix -v /etc/localtime:/etc/localtime:ro -v $HOME/ros_workspaces/tactical_retreat_ws/src/typedb_tactics:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics tactical_retreat typedb server
```

Mount ros_typedb as well:

```Bash
docker run -d --rm --name tactical_retreat --runtime=nvidia --gpus all -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 -v /tmp/.X11-unix:/tmp/.X11-unix -v /etc/localtime:/etc/localtime:ro -v $HOME/ros_workspaces/tactical_retreat_ws/src/typedb_tactics:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics -v $HOME/ros_workspaces/tactical_retreat_ws/src/ros_monitors:/home/ubuntu-user/tactical_retreat_ws/src/ros_monitors -v $HOME/ros_workspaces/tactical_retreat_ws/src/ros_typedb:/home/ubuntu-user/tactical_retreat_ws/src/ros_typedb tactical_retreat typedb server
```

Mount ros_monitors as well:

```Bash
docker run -d --rm --name tactical_retreat --runtime=nvidia --gpus all -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 -v /tmp/.X11-unix:/tmp/.X11-unix -v /etc/localtime:/etc/localtime:ro -v $HOME/ros_workspaces/tactical_retreat_ws/src/typedb_tactics:/home/ubuntu-user/tactical_retreat_ws/src/typedb_tactics -v $HOME/ros_workspaces/tactical_retreat_ws/src/ros_monitors:/home/ubuntu-user/tactical_retreat_ws/src/ros_monitors tactical_retreat typedb server
```

**Note:** Use the correct image name, if you got the img from the github registry use `ghcr.io/kas-lab/typedb_tactics:latest` instead of `tactical_retreat`

Start new terminal in the container:

```Bash
docker exec -it tactical_retreat bash
```

### Test

```Bash
colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics
```
