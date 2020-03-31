#!/usr/bin/env python3

import os
from argparse import ArgumentParser
from shutil import copyfile, copytree, rmtree
import docker
import yaml

BASE_DIRECTORY = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def parse_arguments():
    parser = ArgumentParser(description="Build docker image for model deployment")
    parser.add_argument("--image_name", type=str, help="Name of docker output image", required=True)
    parser.add_argument("--docker_env", type=str, help="Docker environment to use", default="py37")
    parser.add_argument(
        "--mdai_folder", type=str, help="path of mdai deployment folder", default=None
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--target_folder", type=str, help="path of model folder", default=None)
    group.add_argument("--config_file", type=str, help="path to yaml config file", default=None)
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    client = docker.from_env()
    cwd = os.getcwd()

    args = parse_arguments()
    config_file = args.config_file

    if config_file is not None:
        config_file = os.path.abspath(config_file)
        parent_dir = os.path.dirname(config_file)
        os.chdir(parent_dir)

        with open(config_file, "r") as stream:
            data = yaml.safe_load(stream)
            docker_env = data["base_image"]
            target_folder = os.path.abspath(data["paths"]["model_folder"])
            mdai_folder = os.path.abspath(data["paths"]["mdai_folder"])

        os.chdir(cwd)
    else:
        docker_env = args.docker_env
        target_folder = os.path.abspath(args.target_folder)

        if args.mdai_folder is None:  # If None, defaults to root of target folder
            mdai_folder = target_folder
        else:
            mdai_folder = os.path.abspath(args.mdai_folder)

    docker_image = args.image_name

    os.chdir(os.path.join(BASE_DIRECTORY, "mdai"))

    src_dockerfile = os.path.join(BASE_DIRECTORY, "docker", docker_env, "Dockerfile")
    dest_dockerfile = "./Dockerfile"
    print(f"\nCopying Dockerfile from {src_dockerfile} to {dest_dockerfile} ...")
    copyfile(src_dockerfile, dest_dockerfile)

    src_lib = target_folder
    dest_lib = "./lib"
    print(f"\nCopying target dir from {src_lib} to {dest_lib} ...")
    copytree(src_lib, dest_lib)

    try:
        print(f"\nBuilding docker image {docker_image} ...\n")
        response = client.api.build(path=".", tag=docker_image, quiet=False, decode=True)
        for line in response:
            if list(line.keys())[0] in ("stream", "error"):
                value = list(line.values())[0]
                if value:
                    print(value.strip())
    except docker.errors.APIError as e:
        print("\nBuild Error: {}".format(e))
    finally:
        print("\nRemoving copied files...")
        os.remove(dest_dockerfile)
        rmtree(dest_lib)
        os.chdir(cwd)
