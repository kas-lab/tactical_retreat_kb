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

Dev with Nvidia GPU:
```Bash
docker run -it --rm --gpus all --runtime=nvidia --name rebet -e DISPLAY=$DISPLAY -e QT_X11_NO_MITSHM=1 -e NVIDIA_VISIBLE_DEVICES=all -e NVIDIA_DRIVER_CAPABILITIES=all -v /dev/dri:/dev/dri -v /tmp/.X11-unix:/tmp/.X11-unix -v /etc/localtime:/etc/localtime:ro -v $HOME/rebet_ws/src/typedb_tactics:/home/ubuntu-user/rebet_ws/src/typedb_tactics rebet
```
