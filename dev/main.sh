#!/usr/bin/env bash

MODEL_DIRECTORY=$1
MDAI_DIRECTORY=$2

while true; do
  python server.py &
  PID=$!
  inotifywait -e modify  $MODEL_DIRECTORY/* $MDAI_DIRECTORY/*
  kill $PID
done
