#!/usr/bin/env python3

import os
from argparse import ArgumentParser
from shutil import copyfile, copytree
import docker
import json
import sys

BASE_DIRECTORY = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
INFO_FILE = "/tmp/mdai-model.info"

HELPER_DIR = os.path.join(BASE_DIRECTORY, "scripts")
sys.path.insert(0, HELPER_DIR)

hot_reload_values = {
    "--COPY--": [
        "COPY main.sh /src/",
        'RUN ["chmod", "+x", "/src/main.sh"]',
        "RUN apt-get update",
        "RUN apt-get install -y inotify-tools",
    ],
    "--COMMAND--": ['CMD ["sh", "-c", "./main.sh /src/lib /src/lib/$MDAI_PATH"]'],
}


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
    parser.add_argument(
        "--hot-reload", action="store_true", help="allows model files to be hot reloaded"
    )
    args = parser.parse_args()
    return args


def copy_files(target_folder, docker_env, hot_reload):
    if hot_reload:
        placeholder_values = hot_reload_values
    else:
        placeholder_values = helper.PLACEHOLDER_VALUES

    dest_dockerfile = helper.process_dockerfile(docker_env, placeholder_values)

    src_lib = target_folder
    dest_lib = "./lib"
    print(f"\nCopying target dir from {src_lib} to {dest_lib} ...")
    copytree(src_lib, dest_lib)

    src_executable = os.path.join(BASE_DIRECTORY, "dev", "main.sh")
    dest_executable = "main.sh"
    print(f"\nCopying executable dir from {src_executable} to {dest_executable} ...")
    copyfile(src_executable, dest_executable)

    copies = [dest_dockerfile, dest_lib, dest_executable]
    return [os.path.abspath(file_copy) for file_copy in copies]


if __name__ == "__main__":
    import helper

    client = docker.from_env()
    cwd = os.getcwd()

    args = parse_arguments()
    hot_reload = args.hot_reload
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
    os.chdir(os.path.join(BASE_DIRECTORY, "mdai"))
    copies = copy_files(target_folder, docker_env, hot_reload)

    with open(INFO_FILE, "w") as f:
        info = {"model_path": target_folder}
        if hot_reload:
            info["dev"] = True
        else:
            info["dev"] = False
        f.write(json.dumps(info))

    try:
        helper.build_image(client, docker_image, relative_mdai_folder)
    except docker.errors as e:
        print("\nBuild Error: {}".format(e))
    finally:
        helper.remove_files(copies)
        os.chdir(cwd)
