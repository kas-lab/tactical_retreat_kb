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

Start dev container with Nvidia GPU and run typedb core:
```Bash
docker run --rm --gpus all --runtime=nvidia --name rebet -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 -e NVIDIA_VISIBLE_DEVICES=all -e NVIDIA_DRIVER_CAPABILITIES=all -v /dev/dri:/dev/dri -v /tmp/.X11-unix:/tmp/.X11-unix -v /etc/localtime:/etc/localtime:ro -v $HOME/rebet_ws/src/typedb_tactics:/home/ubuntu-user/rebet_ws/src/typedb_tactics rebet typedb server
```

Start dev container run typedb core:
```Bash
docker run -d --rm --name rebet -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1  -v /tmp/.X11-unix:/tmp/.X11-unix -v /etc/localtime:/etc/localtime:ro -v $HOME/ros_workspaces/rebet_ws/src/typedb_tactics:/home/ubuntu-user/rebet_ws/src/typedb_tactics rebet typedb server
```


Start new terminal in the container:
```Bash
docker exec -it rebet bash
```