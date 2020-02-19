#!/usr/bin/env bash

PWD=$(pwd)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

DOCKER_ENV=$1
DOCKER_IMAGE=$2

if [[ "$3" = /* ]]; then
  # absolute path provided
  TARGET_DIR=$3
else
  # relative path provided
  TARGET_DIR=$PWD/$3
fi

DOCKERFILE_PATH="$DIR/../docker/$DOCKER_ENV/Dockerfile"

cd $DIR/../mdai

echo ""
echo "Copying Dockerfile from $DOCKERFILE_PATH to ./Dockerfile ..."
cp $DIR/../docker/$DOCKER_ENV/Dockerfile ./Dockerfile

echo ""
echo "Copying target dir from $TARGET_DIR to ./lib ..."
cp -r $TARGET_DIR ./lib

echo ""
echo "Building docker image $DOCKER_IMAGE ..."
docker build -t $DOCKER_IMAGE .

echo ""
echo "Removing copied files..."
rm ./Dockerfile
rm -r ./lib

echo ""
echo "...Done."
echo ""

cd $PWD
