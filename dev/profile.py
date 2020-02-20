#!/usr/bin/env python3
import docker
import sys
import json


EXITED = 'exited'
MODEL_NAME = "model-dev"
KB_VALUE = 1000
KIB_VALUE = 1024


def getstats(container):
    result = {}
    stats = container.stats(stream=False)
    if(container.status == EXITED or not bool(stats['memory_stats'])):
        print('Error: Docker container stopped', file=sys.stderr)
        return

    result['max_memory_usage'] = FormatMemory(stats['memory_stats']['max_usage'])
    result['memory_limit'] = FormatMemory(stats['memory_stats']['limit'])
    result['cpu_total_usage'] = stats['cpu_stats']['cpu_usage']['total_usage']
    result['cpu_system_usage'] = stats['cpu_stats']['system_cpu_usage']
    result['online_cpus'] = stats['cpu_stats']['online_cpus']
    print(json.dumps(result, indent=4), file=sys.stdout)


def FormatMemory(memory):
    if memory < KB_VALUE:
        return FormatMemoryHelper(memory, KB_VALUE)
    else:
        return FormatMemoryHelper(memory, KB_VALUE) + " (" + FormatMemoryHelper(memory, KIB_VALUE) + ")"


def FormatMemoryHelper(memory, divisor):
    count = 0
    while(memory // divisor > 0):
        memory = memory / divisor
        count += 1

    memory = round(memory, 2)
    return str(memory) + getprefix(count, divisor)


def getprefix(count, divisor):
    byte_suffixes = {
        0: "B",
        1: "KB",
        2: "MB",
        3: "GB",
        4: "TB"
    }
    ibyte_suffixes = {
        0: "B",
        1: "KiB",
        2: "MiB",
        3: "GiB",
        4: "TiB"
    }

    if divisor == KB_VALUE:
        return byte_suffixes[count]
    else:
        return ibyte_suffixes[count]


if __name__ == "__main__":
    if(len(sys.argv) == 2):
        MODEL_NAME = sys.argv[1]

    client = docker.from_env()
    try:
        container = client.containers.get(MODEL_NAME)
        getstats(container)
    except (docker.errors.NotFound, docker.errors.APIError) as e:
        print(e, file=sys.stderr)
