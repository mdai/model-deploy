import sys
import os
import logging
import msgpack
from flask import Flask, Response, abort, request, jsonify
from waitress import serve

LIB_PATH = os.path.join(os.getcwd(), "lib")
sys.path.insert(0, LIB_PATH)

mdai_model = None
mdai_model_status = "PENDING"

app = Flask(__name__)


@app.route("/inference", methods=["POST"])
def inference():
    """
    Route for model inference.

    The POST body is msgpack-serialized binary data with the follow schema:

    {
        "instances": [
            {
                "file": "bytes"
                "tags": {
                    "StudyInstanceUID": "str",
                    "SeriesInstanceUID": "str",
                    "SOPInstanceUID": "str",
                    ...
                }
            },
            ...
        ],
        "args": {
            "arg1": "str",
            "arg2": "str",
            ...
        }
    }

    Model scope specifies whether an entire study, series, or instance is given to the model.
    If the model scope is 'INSTANCE', then `instances` will be a single instance (list length of 1).
    If the model scope is 'SERIES', then `instances` will be a list of all instances in a series.
    If the model scope is 'STUDY', then `instances` will be a list of all instances in a study.

    The additional `args` dict supply values that may be used in a given run.

    For a single instance dict, `files` is the raw binary data representing a DICOM file, and
    can be loaded using: `ds = pydicom.dcmread(BytesIO(instance["file"]))`.

    The response body should be the msgpack-serialized binary data of the results:

    [
        {
            "type": "str", // 'NONE', 'ANNOTATION', 'IMAGE', 'DICOM', 'TEXT'
            "study_uid": "str",
            "series_uid": "str",
            "instance_uid": "str",
            "frame_number": "int",
            "class_index": "int",
            "data": {},
            "probability": "float",
            "explanations": [
                {
                    "name": "str",
                    "description": "str",
                    "content": "bytes",
                    "content_type": "str",
                },
                ...
            ],
        },
        ...
    ]

    The DICOM UIDs must be supplied based on the scope of the label attached to `class_index`.
    """
    if not request.content_type == "application/msgpack":
        abort(400)

    data = msgpack.unpackb(request.get_data(), raw=False)

    global mdai_model_status

    try:
        mdai_model_status = "BUSY"
        results = mdai_model.predict(data)
    except Exception as e:
        logging.exception(e)
        abort(500)
    finally:
        mdai_model_status = "READY"

    resp = Response(msgpack.packb(results, use_bin_type=True))
    resp.headers["Content-Type"] = "application/msgpack"
    return resp


@app.route("/status", methods=["GET"])
def status():
    return jsonify({"status": mdai_model_status})


@app.route("/healthz", methods=["GET"])
def healthz():
    """Route for Kubernetes liveness check.
    """
    return "", 200


if __name__ == "__main__":
    from mdai_deploy import MDAIModel

    mdai_model = MDAIModel()

    serve(app, listen="*:6324")
