#!/usr/bin/env python3

import os
from argparse import ArgumentParser
import helper


def parse_arguments():
    parser = ArgumentParser(description="Build docker image for model deployment")
    parser.add_argument("--target_folder", type=str, help="path of model folder", required=True)
    parser.add_argument("--image_name", type=str, help="Name of docker output image", required=True)
    parser.add_argument("--docker_env", type=str, help="Docker environment to use", default="py37")
    parser.add_argument(
        "--mdai_folder", type=str, help="path of mdai deployment folder", default=".mdai"
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":

    args = parse_arguments()
    helper.create_docker_image(args)
