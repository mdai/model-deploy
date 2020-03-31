#!/usr/bin/env bash

MODEL_DIRECTORY=$1

while true; do
  python server.py &
  PID=$!
  inotifywait -e modify  $MODEL_DIRECTORY/*
  kill $PID
done
