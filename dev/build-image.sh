#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

TARGET_DIR=$1

$DIR/../scripts/build-image.py --docker_env py37 --image_name model-dev:latest --target_folder $TARGET_DIR
