#!/usr/bin/env python3

from preprocess import process_data
import sys
import requests
import os
import json
import msgpack
from argparse import ArgumentParser

INFERENCE_ENDPOINT = "http://localhost:6324/inference"
INDENT_SPACES = 4


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


def parse_arguments():
    parser = ArgumentParser(description="Send Dicom files to /inference")
    parser.add_argument("path", type=str, help="Path to DICOM file(s)")
    parser.add_argument("--raw", action="store_true", help="output raw output data")
    parser.add_argument("--pretty", action="store_true", help="prettify json output")
    args = parser.parse_args()
    path = args.path
    output_raw = args.raw
    output_pretty = args.pretty
    return path, output_raw, output_pretty


def output_json(data):
    if data is not None:
        indent = None

        if not output_raw:
            for instance in data:
                instance.pop("data", None)
                instance.pop("explanations", None)

        if output_pretty:
            indent = INDENT_SPACES
        json_data = json.dumps(data, indent=indent)
        print(json_data, file=sys.stdout, flush=True)


if __name__ == "__main__":
    path, output_raw, output_pretty = parse_arguments()
    if not os.path.exists(path):
        print("Error: Path for data does not exist", file=sys.stderr)
    else:
        data = make_inference(path)
        output_json(data)
