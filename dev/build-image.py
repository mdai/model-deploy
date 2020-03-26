#!/usr/bin/env python3

import os
from argparse import ArgumentParser
from shutil import copyfile, copytree, rmtree
import docker
import json

BASE_DIRECTORY = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
INFO_FILE = "/tmp/mdai-model.info"


def parse_arguments():
    parser = ArgumentParser(description="Build docker image for model deployment")
    parser.add_argument("--image_name", type=str, help="Name of docker output image", required=True)
    parser.add_argument("--target_folder", type=str, help="path of model folder", required=True)
    parser.add_argument("--docker_env", type=str, help="Docker environment to use", default="py37")
    parser.add_argument(
        "--hot-reload", action="store_true", help="allows model files to be hot reloaded"
    )
    args = parser.parse_args()
    return args


def copy_dockerfile(docker_env):
    src_dockerfile = os.path.join(BASE_DIRECTORY, "docker", docker_env, "Dockerfile")
    dest_dockerfile = "./Dockerfile"
    print(f"\nCopying Dockerfile from {src_dockerfile} to {dest_dockerfile} ...")
    copyfile(src_dockerfile, dest_dockerfile)
    return dest_dockerfile


def hot_reload_copy(target_folder, docker_env):

    dest_dockerfile = copy_dockerfile(docker_env)

    src_executable = os.path.join(BASE_DIRECTORY, "dev", "main.sh")
    dest_executable = "main.sh"
    print(f"\nCopying executable dir from {src_executable} to {dest_executable} ...")
    copyfile(src_executable, dest_executable)

    src_requirements = os.path.join(target_folder, "requirements.txt")
    dest_requirements = "model-requirements.txt"
    print(f"\nCopying requirements from {src_requirements} to {dest_requirements} ...")
    copyfile(src_requirements, dest_requirements)

    copies = [dest_dockerfile, dest_executable, dest_requirements]
    return [os.path.abspath(file_copy) for file_copy in copies]


def standard_copy(target_folder, docker_env):

    dest_dockerfile = copy_dockerfile(docker_env)

    src_lib = target_folder
    dest_lib = "./lib"
    print(f"\nCopying target dir from {src_lib} to {dest_lib} ...")
    copytree(src_lib, dest_lib)

    copies = [dest_dockerfile, dest_lib]
    return [os.path.abspath(file_copy) for file_copy in copies]


if __name__ == "__main__":
    client = docker.from_env()
    cwd = os.getcwd()

    args = parse_arguments()
    docker_env = args.docker_env
    docker_image = args.image_name
    hot_reload = args.hot_reload
    target_folder = os.path.abspath(args.target_folder)

    if hot_reload:
        if docker_env == "py37":
            docker_env = "py37-dev"
        else:
            print("environment does not support hot reload")
            exit()

    os.chdir(os.path.join(BASE_DIRECTORY, "mdai"))

    if hot_reload:
        copies = hot_reload_copy(target_folder, docker_env)
    else:
        copies = standard_copy(target_folder, docker_env)

    with open(INFO_FILE, "w") as f:
        info = {"model_path": target_folder}
        if hot_reload:
            info["dev"] = True
        else:
            info["dev"] = False
        f.write(json.dumps(info))

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
        for file_copy in copies:
            if os.path.isdir(file_copy):
                rmtree(file_copy)
            else:
                os.remove(file_copy)
        os.chdir(cwd)
