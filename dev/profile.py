#!/usr/bin/env python3

import sys
import json
import docker


EXITED = "exited"
MODEL_NAME = "model-dev"
KB_VALUE = 1000
KIB_VALUE = 1024


def get_stats(container):
    result = {}
    stats = container.stats(stream=False)
    if container.status == EXITED or not bool(stats["memory_stats"]):
        print("Error: Docker container stopped", file=sys.stderr)
        return

    result["max_memory_usage"] = format_memory(stats["memory_stats"]["max_usage"])
    result["memory_limit"] = format_memory(stats["memory_stats"]["limit"])
    result["cpu_total_usage"] = stats["cpu_stats"]["cpu_usage"]["total_usage"]
    result["cpu_system_usage"] = stats["cpu_stats"]["system_cpu_usage"]
    result["online_cpus"] = stats["cpu_stats"]["online_cpus"]
    print(json.dumps(result, indent=4), file=sys.stdout)


def format_memory(memory):
    def _helper(divisor):
        _memory = memory
        count = 0
        while _memory // divisor > 0:
            _memory = _memory / divisor
            count += 1
        _memory = round(_memory, 2)
        return str(_memory) + get_prefix(count, divisor)

    if memory < KB_VALUE:
        return _helper(KB_VALUE)
    else:
        return f"{_helper(KB_VALUE)} ({_helper(KIB_VALUE)})"


def get_prefix(count, divisor):
    byte_suffixes = {0: "B", 1: "KB", 2: "MB", 3: "GB", 4: "TB"}
    ibyte_suffixes = {0: "B", 1: "KiB", 2: "MiB", 3: "GiB", 4: "TiB"}

    if divisor == KB_VALUE:
        return byte_suffixes[count]
    else:
        return ibyte_suffixes[count]


if __name__ == "__main__":
    if len(sys.argv) == 2:
        MODEL_NAME = sys.argv[1]

    client = docker.from_env()
    try:
        container = client.containers.get(MODEL_NAME)
        get_stats(container)
    except (docker.errors.NotFound, docker.errors.APIError) as e:
        print(e, file=sys.stderr)
