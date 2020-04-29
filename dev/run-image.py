#!/usr/bin/env python3

import docker
import os
import json

INFO_FILE = "/tmp/mdai-model.info"

if __name__ == "__main__":
    client = docker.from_env()
    try:
        container = client.containers.get("model-dev")
        container.stop()
        container.remove()
    except docker.errors.NotFound:
        pass

    if os.path.exists(INFO_FILE):
        with open(INFO_FILE, "r") as f:
            model_info = json.loads(f.read())

    runtime = None
    if model_info["device_type"] == "gpu":
        runtime = "nvidia"

    if model_info["dev"] is True:
        client.containers.run(
            "model-dev:latest",
            name="model-dev",
            network="mdai-dev",
            ports={"6324/tcp": 6324},
            volumes={model_info["model_path"]: {"bind": "/src/lib", "mode": "rw"}},
            detach=True,
            runtime=runtime,
        )
    else:
        client.containers.run(
            "model-dev:latest",
            name="model-dev",
            network="mdai-dev",
            ports={"6324/tcp": 6324},
            detach=True,
            runtime=runtime,
        )
    print("Server listening on localhost port 6324")
