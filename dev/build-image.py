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
    "{{PARENT_IMAGE}}": [],
    "{{COPY}}": [
        "COPY main.sh /src/",
        'RUN ["chmod", "+x", "/src/main.sh"]',
        "RUN apt-get update",
        "RUN apt-get install -y inotify-tools",
    ],
    "{{COMMAND}}": [
        'CMD ["/bin/bash", "-c", "source activate mdai-env ; ./main.sh /src/lib /src/lib/$MDAI_PATH"]'
    ],
    "{{ENV}}": [],
}


def parse_arguments():
    parser = ArgumentParser(description="Build docker image for model deployment")
    parser.add_argument("--target_folder", type=str, help="path of model folder", required=True)
    parser.add_argument("--image_name", type=str, help="Name of docker output image", required=True)
    parser.add_argument("--docker_env", type=str, help="Docker environment to use", default="py37")
    parser.add_argument(
        "--hot_reload", action="store_true", help="allows model files to be hot reloaded"
    )
    parser.add_argument(
        "--mdai_folder", type=str, help="path of mdai deployment folder", default=".mdai"
    )
    args = parser.parse_args()
    return args


def copy_files(target_folder, docker_env, placeholder_values):
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


def write_info_file(args):
    target_folder = os.path.abspath(args.target_folder)
    with open(INFO_FILE, "w") as f:
        info = {"model_path": target_folder}
        if hot_reload:
            info["dev"] = True
        else:
            info["dev"] = False

        _, _, config_file = helper.get_paths(args)
        config = helper.process_config_file(config_file)

        if config.get("device_type") == "gpu":
            info["device_type"] = "gpu"
        else:
            info["device_type"] = "cpu"

        f.write(json.dumps(info))


if __name__ == "__main__":
    import helper

    args = parse_arguments()
    hot_reload = args.hot_reload
    write_info_file(args)

    if hot_reload:
        client = docker.from_env()
        cwd = os.getcwd()

        docker_env = args.docker_env
        docker_image = args.image_name
        env = None
        config_file = None

        target_folder, mdai_folder, config_path = helper.get_paths(args)
        # Detect config file if exists
        if os.path.exists(config_path):
            config_file = config_path

        # Prioritize config file values if it exists
        if config_file is not None:
            config = helper.process_config_file(config_file)

        placeholder_values = hot_reload_values

        helper.resolve_parent_image(hot, config, helper.PARENT_IMAGE_DICT)
        helper.add_env_variables(placeholder_values, config.get("env"))
        relative_mdai_folder = os.path.relpath(mdai_folder, target_folder)
        os.chdir(os.path.join(BASE_DIRECTORY, "mdai"))
        copies = copy_files(target_folder, config["base_image"], placeholder_values)

        try:
            helper.build_image(client, docker_image, relative_mdai_folder)
        except Exception as e:
            print("\nBuild Error: {}".format(e))
        finally:
            helper.remove_files(copies)
            os.chdir(cwd)
    else:
        helper.create_docker_image(args)
