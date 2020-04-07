import os
import yaml
from shutil import rmtree


BASE_DIRECTORY = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

PLACEHOLDER_VALUES = {
    "{{COPY}}": ["COPY lib /src/lib/"],
    "{{COMMAND}}": ['CMD ["python", "server.py"]'],
    "{{ENV}}": [],
}


def replace_lines(infile, outfile, replace_dict):
    for line in infile:
        key = line.rstrip()
        if key in replace_dict:
            outfile.write("\n".join(replace_dict[key]))
        else:
            outfile.write(line)


def process_dockerfile(docker_env, placeholder_values):
    src_dockerfile = os.path.join(BASE_DIRECTORY, "docker", docker_env, "Dockerfile.template")
    dest_dockerfile = "./Dockerfile"
    print(f"\nCopying Dockerfile from {src_dockerfile} to {dest_dockerfile} ...")
    with open(src_dockerfile, "r") as infile, open(dest_dockerfile, "w") as outfile:
        replace_lines(infile, outfile, placeholder_values)
    return dest_dockerfile


def process_config_file(config_file):
    cwd = os.getcwd()
    config_file = os.path.abspath(config_file)
    parent_dir = os.path.dirname(config_file)
    os.chdir(parent_dir)

    with open(config_file, "r") as stream:
        data = yaml.safe_load(stream)
        docker_env = data["base_image"]
        target_folder = os.path.abspath(data["paths"]["model_folder"])
        mdai_folder = os.path.abspath(data["paths"]["mdai_folder"])
        env = data.get("env")

        os.chdir(cwd)
    return docker_env, target_folder, mdai_folder, env


def get_paths(args):
    target_folder = os.path.abspath(args.target_folder)

    if args.mdai_folder is None:  # If None, defaults to .mdai directory of target folder
        mdai_folder = os.path.join(target_folder, ".mdai")
    else:
        mdai_folder = os.path.abspath(args.mdai_folder)

    config_path = os.path.join(mdai_folder, "config.yaml")

    return target_folder, mdai_folder, config_path


def remove_files(copies):
    print("\nRemoving copied files...")
    for file_copy in copies:
        if os.path.isdir(file_copy):
            rmtree(file_copy)
        else:
            os.remove(file_copy)


def build_image(client, docker_image, relative_mdai_folder):
    print(f"\nBuilding docker image {docker_image} ...\n")
    build_dict = {"MDAI_PATH": relative_mdai_folder}
    response = client.api.build(
        path=".", tag=docker_image, quiet=False, decode=True, buildargs=build_dict
    )
    for line in response:
        if list(line.keys())[0] in ("stream", "error"):
            value = list(line.values())[0]
            if value:
                print(value.strip())


def add_env_variables(placeholder_values, env_variables):
    ENV = "{{ENV}}"
    if env_variables is None:
        return
    for key in env_variables:
        arg_string = f"ARG {key}"
        env_string = f"ENV {key}={env_variables[key]}"
        placeholder_values[ENV].append(arg_string)
        placeholder_values[ENV].append(env_string)
