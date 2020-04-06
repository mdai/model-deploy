#!/usr/bin/env python3

import os
from argparse import ArgumentParser
from shutil import copytree
import docker
import helper


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


def copy_files(target_folder, docker_env):
    dest_dockerfile = helper.process_dockerfile(docker_env, helper.PLACEHOLDER_VALUES)

    src_lib = target_folder
    dest_lib = "./lib"
    print(f"\nCopying target dir from {src_lib} to {dest_lib} ...")
    copytree(src_lib, dest_lib)

    copies = [dest_lib, dest_dockerfile]
    return [os.path.abspath(file_copy) for file_copy in copies]


if __name__ == "__main__":
    client = docker.from_env()
    cwd = os.getcwd()

    args = parse_arguments()
    docker_env = args.docker_env
    config_file = args.config_file
    docker_env = args.docker_env
    docker_image = args.image_name

    if config_file is None:
        target_folder, mdai_folder, config_path = helper.get_paths(args)

        # Detect config file if exists
        if os.path.exists(config_path):
            config_file = config_path

    # Prioritize config file values if it exists
    if config_file is not None:
        docker_env, target_folder, mdai_folder = helper.process_config_file(config_file)

    relative_mdai_folder = os.path.relpath(mdai_folder, target_folder)
    os.chdir(os.path.join(helper.BASE_DIRECTORY, "mdai"))
    copies = copy_files(target_folder, docker_env)

    try:
        helper.build_image(client, docker_image, relative_mdai_folder)
    except docker.errors.APIError as e:
        print("\nBuild Error: {}".format(e))
    finally:
        helper.remove_files(copies)
        os.chdir(cwd)
