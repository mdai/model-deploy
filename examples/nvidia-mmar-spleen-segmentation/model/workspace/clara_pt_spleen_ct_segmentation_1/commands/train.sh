#!/usr/bin/env bash

my_dir="$(dirname "$0")"
. $my_dir/set_env.sh

echo "MMAR_ROOT set to $MMAR_ROOT"
additional_options="$*"

# Data list containing all data
CONFIG_FILE=config/config_train.json
ENVIRONMENT_FILE=config/environment.json

python3 -u -m medl.apps.train \
    -m $MMAR_ROOT \
    -c $CONFIG_FILE \
    -e $ENVIRONMENT_FILE \
    --write_train_stats \
    --set \
    print_conf=True \
    epochs=1260 \
    learning_rate=0.0002 \
    num_interval_per_valid=20 \
    multi_gpu=False \
    cudnn_benchmark=False \
    dont_load_ckpt_model=True \
    ${additional_options}
