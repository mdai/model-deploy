#!/usr/bin/env python3

import os
from argparse import ArgumentParser
from shutil import copyfile, copytree, rmtree
import docker

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
