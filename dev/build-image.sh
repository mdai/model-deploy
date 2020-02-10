#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

TARGET_DIR=$1

$DIR/../scripts/build-image.sh py37 model-dev:latest $TARGET_DIR
