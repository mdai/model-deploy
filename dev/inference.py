#!/usr/bin/env python3

from .preprocess import process_data
import sys
import requests
import os
import json
import msgpack

INFERENCE_ENDPOINT = "http://localhost:6324/inference"


def make_inference(path):
    payload = process_data(path)
    headers = {"content-type": "application/msgpack"}
    r = requests.post(INFERENCE_ENDPOINT, data=payload, headers=headers)
    if r.status_code == 200:
        return msgpack.unpackb(r.content)
    else:
        print(
            "Error: status code {} when contacting endpoint".format(r.status_code), file=sys.stderr
        )
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Argument required for data", file=sys.stderr)
    else:
        path = sys.argv[1]
        if not os.path.exists(path):
            print("Error: Path for data does not exist", file=sys.stderr)
        else:
            data = make_inference(path)
            if data is not None:
                json_data = json.dumps(data)
                print(json_data, file=sys.stdout, flush=True)
