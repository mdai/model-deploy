#!/usr/bin/env bash

my_dir="$(dirname "$0")"
. $my_dir/set_env.sh

# Data list containing all data

export CKPT_DIR=$MMAR_ROOT/models

python3 -u -m nvmidl.apps.export \
    --model_file_format CKPT \
    --model_file_path $CKPT_DIR \
    --model_name model \
    --input_node_names "NV_MODEL_INPUT" \
    --output_node_names NV_MODEL_OUTPUT \
    --trt_min_seg_size 50
