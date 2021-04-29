import sys
import os
import logging
from threading import Lock
import msgpack
from fastapi import FastAPI, HTTPException, Request, Response
from concurrent.futures import ThreadPoolExecutor
import asyncio
from hypercorn.config import Config
from hypercorn.asyncio import serve

from validation import OutputValidator

# To handle compressed DICOM image data
import pylibjpeg

# Used for model invalidation. If the minimum version required is increased beyond this value, then
# the model built using this version will return an error. Version should be in semver format.
MDAI_DEPLOY_API_VERSION = "0.3"

LIB_PATH = os.path.join(os.getcwd(), "lib")
sys.path.insert(0, LIB_PATH)
MDAI_PATH = os.path.join(LIB_PATH, os.environ["MDAI_PATH"])
sys.path.insert(1, MDAI_PATH)

logger = logging.getLogger("model")
logger.setLevel(logging.INFO)

mdai_model = None
mdai_model_ready = False
mdai_model_lock = Lock()

output_validator = OutputValidator()
executor = ThreadPoolExecutor(max_workers=1)

app = FastAPI()


@app.post("/inference")
async def inference(request: Request):
    """
    Route for model inference.

    The POST body is msgpack-serialized binary data with the follow schema:

    {
        "files": [
            {
                "content": "bytes",
                "content_type": "str", # MIME type, e.g. 'application/dicom'
            },
            ...
        ],
        "annotations": [
            {
                "study_uid": "str",
                "series_uid": "str",
                "instance_uid": "str",
                "frame_number": "int",
                "class_index": "int",
                "data": "any",
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
    - 'INSTANCE' model scope: `files` will contain a single instance (list length of 1)
    - 'SERIES' model scope: `files` will contain a list of all instances in a series
    - 'STUDY' model scope: `files` will contain a list of all instances in a study

    If multi-frame instances are supported, the model scope must be 'SERIES' or 'STUDY', because
    internally we treat these as DICOM series.

    The additional `args` dict supply values that may be used in a given run.

    For a file with `content_type='application/dicom'`, `content` is the raw binary data
    representing a DICOM file, and can be loaded using:
    `ds = pydicom.dcmread(BytesIO(file["content"]))`.

    The response body should be the msgpack-serialized binary data of the results:

    [
        {
            "type": "str", # 'NONE', 'ANNOTATION', 'IMAGE', 'DICOM', 'TEXT'
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
                    "content_type": "str", # MIME type, e.g. 'image/png'
                },
                ...
            ],
        },
        ...
    ]

    The DICOM UIDs must be supplied based on the scope of the label attached to `class_index`.
    """

    loop = asyncio.get_event_loop()

    if not request.headers["content-type"] == "application/msgpack":
        raise HTTPException(status_code=400)
    body = await request.body()

    def _inference(body):
        data = msgpack.unpackb(body, raw=False)

        try:
            mdai_model_lock.acquire()
            results = mdai_model.predict(data)
        except Exception as e:
            logger.exception(e)
            text = f"Error running model: {str(e)}"
            headers = {"Content-Type": "text/plain"}
            return Response(content=text, status_code=500, headers=headers)
        finally:
            mdai_model_lock.release()

        try:
            output_validator.validate(results)
        except Exception as e:
            logger.exception(e)
            text = f"Invalid data format returned by model: {str(e)}"
            headers = {"Content-Type": "text/plain"}
            return Response(content=text, status_code=500, headers=headers)

        headers = {"Content-Type": "application/msgpack"}
        resp = Response(
            status_code=200, content=msgpack.packb(results, use_bin_type=True), headers=headers
        )
        return resp

    resp = await loop.run_in_executor(executor, _inference, body)
    return resp


@app.post("/testing-on-batch")
async def testing_on_batch(request: Request):
    """
    Route for model metrics evaluation.
    The POST body is msgpack-serialized binary data with the follow schema:

    {
        "files": [
            {
                "content": "bytes",
                "content_type": "str", # MIME type, e.g. 'application/dicom'
            },
            ...
        ],
        "targets": [
            {
                "resource_scope": "str", # 'STUDY', 'SERIES', or 'INSTANCE'
                "resource_uid": "str",
                "target_type": "str", # 'NONE' or 'ANNOTATION'
                "target_class_index": "int",
                "target_annotation_mode": "str",
                "target_data": "any",
            },
            ...
        ],
        "args": {
            "arg1": "str",
            "arg2": "str",
            ...
        }
    }

    The response body should be the msgpack-serialized binary data of the results:

    [
        {
            "name": "str", # For example, 'Mean Squared Error'
            "value": "float",
            "reduction": "str", # 'mean' or 'sum'
        },
        ...
    ]
    """

    loop = asyncio.get_event_loop()

    if not request.headers["content-type"] == "application/msgpack":
        raise HTTPException(status_code=400)
    body = await request.body()

    def _testing_on_batch(body):
        data = msgpack.unpackb(body, raw=False)

        try:
            mdai_model_lock.acquire()
            results = mdai_model.evaluate_on_batch(data)
        except Exception as e:
            logger.exception(e)
            text = f"Error calculating metrics: {str(e)}"
            headers = {"Content-Type": "text/plain"}
            return Response(content=text, status_code=500, headers=headers)
        finally:
            mdai_model_lock.release()

        headers = {"Content-Type": "application/msgpack"}
        resp = Response(
            status_code=200, content=msgpack.packb(results, use_bin_type=True), headers=headers
        )
        return resp

    resp = await loop.run_in_executor(executor, _testing_on_batch, body)
    return resp


@app.post("/reduce-batch-testing-results")
async def reduce_batch_testing_results(request: Request):
    """
    Route for metric reduction.
    The POST body is msgpack-serialized binary data with the follow schema:

    [
        {
            "name": "str", # For example, 'Mean Squared Error'
            "values": "float[]",
            "reduction": "str", # 'mean' or 'sum'
        },
        ...
    ]

    The response body should be the msgpack-serialized binary data of the results:

    [
        {
            "name": "str", # For example, 'Mean Squared Error'
            "reduced_value": "float",
        },
        ...
    ]
    """

    loop = asyncio.get_event_loop()

    if not request.headers["content-type"] == "application/msgpack":
        raise HTTPException(status_code=400)
    body = await request.body()

    def _reduce_batch_testing_results(body):
        data = msgpack.unpackb(body, raw=False)

        try:
            mdai_model_lock.acquire()
            results = []
            for val in data:
                result = {"name": val["name"], "reduced_value": None}
                if val["reduction"].lower() == "sum":
                    result["reduced_value"] = sum(val["values"])
                elif val["reduction"].lower() == "mean":
                    result["reduced_value"] = sum(val["values"]) / len(val["values"])
                results.append(result)
        except Exception as e:
            logger.exception(e)
            text = f"Error in reduction: {str(e)}"
            headers = {"Content-Type": "text/plain"}
            return Response(content=text, status_code=500, headers=headers)
        finally:
            mdai_model_lock.release()

        headers = {"Content-Type": "application/msgpack"}
        resp = Response(
            status_code=200, content=msgpack.packb(results, use_bin_type=True), headers=headers
        )
        return resp

    resp = await loop.run_in_executor(executor, _reduce_batch_testing_results, body)
    return resp


@app.get("/healthz")
def healthz():
    """Route for Kubernetes liveness check."""
    return Response(status_code=200, content="")


@app.get("/ready")
def ready():
    """Route for Kubernetes readiness check."""
    if mdai_model_ready:
        return Response(status_code=200, content="")
    else:
        return Response(status_code=503, content="")


@app.get("/version")
def version():
    """Route for retrieving server version."""
    return Response(status_code=200, content=MDAI_DEPLOY_API_VERSION)


@app.get("/has-testing-metrics")
def has_testing_metrics():
    """Route for metric evaluation check."""
    data = {"hasTestingMetrics": False}
    if hasattr(mdai_model, "evaluate_on_batch") and callable(mdai_model.evaluate_on_batch):
        data["hasTestingMetrics"] = True
    return Response(status_code=200, content=data)


if __name__ == "__main__":

    from mdai_deploy import MDAIModel

    mdai_model = MDAIModel()
    mdai_model_ready = True

    config = Config()
    config.bind = ["0.0.0.0:6324"]
    config.workers = 1

    asyncio.run(serve(app, config))
