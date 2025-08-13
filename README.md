# typedb_tactics

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

Start dev container run typedb core:
```Bash
docker run -d --rm --name rebet -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1  -v /tmp/.X11-unix:/tmp/.X11-unix -v /etc/localtime:/etc/localtime:ro -v $HOME/ros_workspaces/rebet_ws/src/typedb_tactics:/home/ubuntu-user/rebet_ws/src/typedb_tactics rebet typedb server
```


Start new terminal in the container:
```Bash
docker exec -it rebet bash
```

### Test

```Bash
colcon test --event-handlers console_cohesion+ --packages-select typedb_tactics
```

