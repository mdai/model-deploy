#!/usr/bin/env python3

import docker
from argparse import ArgumentParser
import os
from shutil import copyfile, copytree, rmtree
import sys

BASE_DIRECTORY = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def parse_arguments():
    parser = ArgumentParser(description="Build docker image for model deployment")
    parser.add_argument("--docker_env", type=str, help="Docker environment to use", required=True)
    parser.add_argument("--image_name", type=str, help="Name of docker output image", required=True)
    parser.add_argument("--target_folder", type=str, help="path of model folder", required=True)
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    client = docker.from_env()
    cwd = os.getcwd()

    args = parse_arguments()
    docker_env = args.docker_env
    docker_image = args.image_name
    target_folder = os.path.abspath(args.target_folder)

    os.chdir("/".join((BASE_DIRECTORY, "mdai")))

    src_dockerfile = "/".join((BASE_DIRECTORY, "docker", docker_env, "Dockerfile"))
    dest_dockerfile = "./Dockerfile"
    copyfile(src_dockerfile, dest_dockerfile)

    src_lib = target_folder
    dest_lib = "./lib"
    copytree(src_lib, dest_lib)

    try:
        client.images.build(path=".", tag=docker_image, quiet=False)
    except docker.errors.BuildError as e:
        print("Build Error: {}".format(e))
        for line in e.build_log:
            if "stream" in line:
                print(line["stream"].strip(), file=sys.stderr)
    finally:
        os.remove(dest_dockerfile)
        rmtree(dest_lib)
        os.chdir(cwd)
