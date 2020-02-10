#!/usr/bin/env bash

docker stop model-dev
docker rm model-dev
docker run -d --network=mdai-dev --name=model-dev model-dev:latest
