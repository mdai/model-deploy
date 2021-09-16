#!/bin/bash

nvidia-docker run --rm -it --ipc=host \
    -v $(pwd -P)/data:/workspace/data \
    -v $(pwd -P)/eval:/workspace/clara_pt_spleen_ct_segmentation_1/eval \
    spleen-test:latest \
        /workspace/clara_pt_spleen_ct_segmentation_1/commands/infer.sh
