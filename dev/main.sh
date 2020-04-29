#!/usr/bin/env bash

MODEL_DIRECTORY=$1

watchmedo auto-restart -d $MODEL_DIRECTORY -D -R --signal SIGKILL python server.py
