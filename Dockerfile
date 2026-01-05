FROM ros:humble-ros-core-jammy

# Set environment variables for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    sudo \
    curl \
    wget \
    vim \
    git \
    python3-pip \
    python3-vcstool \
    python3-rosdep \
    xvfb \
    htop \
    mesa-utils \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libglx-mesa0 \
    ros-dev-tools \
    xdg-utils \
    software-properties-common \
    apt-transport-https \
    gpg \
    openjdk-11-jre \
    ros-humble-tf2-ros \
    ros-humble-tf2-ros-py \
    ros-humble-tf-transformations \
    flake8 \
    python3-flake8-* \
    python3-ament-flake8 \
    && rm -rf /var/lib/apt/lists/*

RUN rosdep init

## Install TypeDB
RUN gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-key 17507562824cfdcc
RUN gpg --export 17507562824cfdcc | sudo tee /etc/apt/trusted.gpg.d/vaticle.gpg > /dev/null
RUN echo "deb https://repo.typedb.com/public/public-release/deb/ubuntu trusty main" | tee /etc/apt/sources.list.d/vaticle.list > /dev/null

RUN apt-get update && apt-get install -y \
    typedb=2.28.3 \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install typedb-driver==2.28.0

## Install TypeDB studio
RUN sudo mkdir /usr/share/desktop-directories/
RUN wget https://repo.typedb.com/public/public-release/raw/names/typedb-studio-linux-x86_64-deb/versions/2.28.0/typedb-studio-linux-x86_64-2.28.0.deb
RUN dpkg -i typedb-studio-linux-x86_64-2.28.0.deb

## Create ubuntu-user user, disable password, and add it to sudo group
RUN groupadd -g 1000 ubuntu-user \
    && adduser --disabled-password --gid 1000 --uid 1000 --gecos '' ubuntu-user \
    && adduser ubuntu-user sudo

RUN echo 'ubuntu-user ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers
ENV HOME=/home/ubuntu-user
USER ubuntu-user
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR $HOME

## Create alias for TypeDB studio
RUN echo 'alias typedb-studio="/opt/typedb-studio/bin/TypeDB\ Studio"' >> ~/.bashrc

## Create, install deps, and build Rebet workspace
RUN mkdir -p rebet_ws/src
WORKDIR $HOME/rebet_ws/src
COPY dependencies.repos $HOME/rebet_ws/dependencies.repos

WORKDIR $HOME/rebet_ws

ARG DEPS_CACHE_BUSTER
RUN --mount=type=secret,id=gh_token,uid=1000,gid=1000,mode=0400 bash -lc '\
  echo "deps-buster=${DEPS_CACHE_BUSTER}" > /dev/null; \
  tok=$(tr -d "\r\n" < /run/secrets/gh_token); \
  export GIT_TERMINAL_PROMPT=0; \
  git config --global url."https://x-access-token:${tok}@github.com/".insteadOf "https://github.com/"; \
  vcs import --input $HOME/rebet_ws/dependencies.repos src ; \
'

COPY fuzzy $HOME/rebet_ws/src/typedb_tactics/fuzzy
COPY launch $HOME/rebet_ws/src/typedb_tactics/launch
COPY resource $HOME/rebet_ws/src/typedb_tactics/resource
COPY schemas $HOME/rebet_ws/src/typedb_tactics/schemas
COPY test $HOME/rebet_ws/src/typedb_tactics/test
COPY typedb_tactics $HOME/rebet_ws/src/typedb_tactics/typedb_tactics
COPY LICENSE $HOME/rebet_ws/src/typedb_tactics/LICENSE
COPY package.xml $HOME/rebet_ws/src/typedb_tactics/package.xml
COPY setup.cfg $HOME/rebet_ws/src/typedb_tactics/setup.cfg
COPY setup.py $HOME/rebet_ws/src/typedb_tactics/setup.py


WORKDIR $HOME/rebet_ws/
RUN ["/bin/bash", "-c", "source /opt/ros/humble/setup.bash \
    && sudo apt update \
    && rosdep update \
    && rosdep install --from-paths src --ignore-src -r -y \
    && sudo rm -rf /var/lib/apt/lists/"]

## There is a bug with the default setuptools and packaging versions
RUN USER=ubuntu-user python3 -m pip install setuptools==75.8.2  packaging==24.1 empy==3.3.4 pandas==2.0.2 scipy==1.15.2 numpy==1.23.5
RUN ["/bin/bash", "-c", "source /opt/ros/humble/setup.bash \
    && colcon build --symlink-install \
    && echo 'source ~/rebet_ws/install/setup.bash' >> ~/.bashrc"]

RUN sudo apt autoremove -y && sudo rm -rf /var/lib/apt/lists/