# obs-docker


docker build -f Dockerfile -t ubuntu-lxde-obs-container
docker create -v $PWD/home:/home:rw -p 3389:3389 -p 4455:4455 --name ubuntu-lxde-obs-container ubuntu-lxde-obs-container
docker start ubuntu-lxde-obs-container
docker exec -it ubuntu-lxde-obs-container /bin/bash
adduser <username>
