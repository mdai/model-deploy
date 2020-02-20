#!/usr/bin/env bash

docker stop model-dev
docker rm model-dev
docker run -d --network=mdai-dev --name=model-dev -p 6324:6324 model-dev:latest
echo "Server listening on localhost port 6324"
