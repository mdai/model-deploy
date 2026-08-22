import sys
import os
import logging
import asyncio
import shutil
import threading
import traceback
import msgpack
from fastapi import FastAPI, HTTPException, Request, Response
from uvicorn import Config, Server

from validation import OutputValidator

# To handle compressed DICOM image data
import pylibjpeg  # noqa: F401

# Used for model invalidation. If the minimum version required is increased beyond this value, then
# the model built using this version will return an error. Version should be in semver format.
MDAI_DEPLOY_API_VERSION = "0.4"

# Base directory for files pushed ahead of an inference request by /load-files. Input files arrive
# with a relative content_path and are made absolute against this before the model sees them. The
# working directory is owned by root while the container runs as an unprivileged user, so this has
# to point somewhere writable.
DATA_PATH = os.environ.get("MDAI_DATA_PATH", "/tmp/mdai-data")

# How often the server checks whether the client is still waiting for an inference it is running.
# A request that is abandoned -- the caller timed out and moved on -- otherwise runs to completion
# against a socket nobody will read, holding the GPU for work whose result is discarded.
DISCONNECT_POLL_SECONDS = 5

LIB_PATH = os.path.join(os.getcwd(), "lib")
sys.path.insert(0, LIB_PATH)
MDAI_PATH = os.path.join(LIB_PATH, os.environ["MDAI_PATH"])
sys.path.insert(1, MDAI_PATH)

logger = logging.getLogger("model")
logger.setLevel(logging.INFO)

mdai_model = None
mdai_model_ready = False
mdai_model_error = ""

output_validator = OutputValidator()

app = FastAPI()


def _error_response(content: str):
    headers = {"Content-Type": "text/plain"}
    return Response(content, status_code=500, headers=headers)


def _resolve_content_path(content_path):
    """
    Absolute on-disk path for a model input file, rejecting anything that escapes DATA_PATH.
    """
    path = os.path.normpath(os.path.join(DATA_PATH, str(content_path).lstrip("/")))
    if not path.startswith(os.path.join(DATA_PATH, "")):
        raise ValueError(f"Invalid content path: {content_path}")
    return path


def _write_files(files):
    """
    Writes files pushed by /load-files to disk, to be read during a later inference request.
    """
    for file in files:
        path = _resolve_content_path(file["content_path"])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(file["content"])


def _resolve_input_paths(files):
    """
    Rewrites each input file's content_path to its absolute on-disk location, in place. Handles both
    a flat file list and a list of file groups.
    """
    for file in files:
        if isinstance(file, list):
            _resolve_input_paths(file)
        elif file.get("content_path"):
            file["content_path"] = _resolve_content_path(file["content_path"])


def _is_grouped(files):
    """
    True if `files` is a list of file groups rather than a flat list of files.
    """
    return bool(files) and isinstance(files[0], list)


def _input_file_paths(files):
    """
    Every on-disk path referenced by an inference request's files, flat list or grouped.
    """
    paths = []
    for file in files:
        if isinstance(file, list):
            paths.extend(_input_file_paths(file))
        elif file.get("content_path"):
            paths.append(file["content_path"])
    return paths


def _remove_input_files(paths):
    """
    Deletes the input files an inference request consumed, and any directories left empty.

    Files arrive through /load-files and are read once, by the request that follows. Nothing else
    removes them, so without this a pod accumulates every input it has ever been sent until the
    node runs out of disk -- which evicts unrelated pods on the same node, not just this one.
    """
    directories = set()
    for path in paths:
        try:
            os.remove(path)
            directories.add(os.path.dirname(path))
        except FileNotFoundError:
            continue
        except OSError as e:
            logger.warning(f"Could not remove input file {path}: {e}")

    # Walk upwards from the deepest directories, so a study directory is considered after the
    # series directories under it have gone.
    for directory in sorted(directories, key=len, reverse=True):
        while directory.startswith(os.path.join(DATA_PATH, "")):
            try:
                os.rmdir(directory)
            except OSError:
                # Not empty, or gone already: nothing above it can be empty either.
                break
            directory = os.path.dirname(directory)


def _clear_data_path():
    """
    Empties the input file directory. Called at startup so a restarted pod does not inherit the
    files of whatever ran before it -- on a restart-in-place the volume survives the process.
    """
    try:
        shutil.rmtree(DATA_PATH, ignore_errors=True)
        os.makedirs(DATA_PATH, exist_ok=True)
    except OSError as e:
        logger.warning(f"Could not clear {DATA_PATH}: {e}")


async def _watch_for_disconnect(request, cancelled):
    """
    Sets `cancelled` if the client goes away while the model is running.

    The model is handed this event and may consult it to stop early; one that ignores it behaves
    exactly as before. Nothing is force-killed -- the inference is on a worker thread holding the
    GPU, and abandoning it there without unwinding would let the next request start against a
    device that is still busy.
    """
    while not cancelled.is_set():
        try:
            if await request.is_disconnected():
                cancelled.set()
                return
        except Exception:  # noqa: BLE001 - a broken receive channel means the client is gone
            cancelled.set()
            return
        await asyncio.sleep(DISCONNECT_POLL_SECONDS)


def _predict(data, cancelled=None):
    """
    Runs the model over an inference request's files.

    `cancelled` is a threading.Event set when the client stops waiting. It is published on the
    model as `mdai_cancelled` so a long-running model can check it between units of work and
    return early; a model that does not look at it is unaffected.

    As of API version 0.4 `files` may be a list of file groups -- one group per resource in the
    model task's batch -- so that a single request covers a whole batch instead of one resource. A
    model that defines `predict_batch` receives the groups as they are, and can batch across them.
    Every other model is called once per group and keeps the flat-list contract it was written to.
    """
    files = data.get("files") or []
    try:
        mdai_model.mdai_cancelled = cancelled
    except AttributeError:
        # A model that does not accept the attribute simply cannot be cancelled early.
        cancelled = None
    try:
        if not _is_grouped(files):
            return mdai_model.predict(data)

        if hasattr(mdai_model, "predict_batch"):
            return mdai_model.predict_batch(data)

        results = []
        for group in files:
            if cancelled is not None and cancelled.is_set():
                break
            results.extend(mdai_model.predict({**data, "files": group}))
        return results
    finally:
        try:
            mdai_model.mdai_cancelled = None
        except AttributeError:
            pass


@app.post("/load-files")
async def load_files(request: Request):
    """
    Route for loading input files onto the model container's disk ahead of an inference request.

    The POST body is a msgpack-serialized list of {"content": bytes, "content_path": str}. The
    inference request that follows refers to the same content_path with a null `content`, which
    keeps a large batch's pixel data out of the inference request body.
    """
    if not request.headers["content-type"] == "application/msgpack":
        raise HTTPException(status_code=400)

    try:
        body = await request.body()
        files = await asyncio.to_thread(msgpack.unpackb, body, raw=False)
        del body
    except Exception as e:
        logger.exception(e)
        return _error_response("Error reading input data")

    try:
        await asyncio.to_thread(_write_files, files)
    except Exception as e:
        logger.exception(e)
        return _error_response(f"Error loading files: {e}")

    return Response(status_code=200, content="")


@app.post("/inference")
async def inference(request: Request):
    """
    Route for model inference.

    The POST body is msgpack-serialized binary data with the follow schema:

    {
        "input_data_source": "str", # 'MEMORY' or 'DISK'
        "files": [
            {
                "content": "bytes",       # null when input_data_source is not 'MEMORY'
                "content_path": "str",     # set instead of `content`, see /load-files
                "content_type": "str",     # MIME type, e.g. 'application/dicom'
            },
            ...
        ],
        "annotations": [
            {
                "id": "str",
                "label_id": "str",
                "study_uid": "str",
                "series_uid": "str",
                "instance_uid": "str",
                "frame_number": "int",
                "data": "any",
                "parent_id": "str"
            },
            ...
        ],
        "label_classes": [
            {
                "class_index": "int",
                "label": {
                    "id": "str",
                    "name": "str",
                    "type": "str", # 'GLOBAL', 'LOCAL'
                    "scope": "str", # 'INSTANCE', 'SERIES', 'STUDY'
                    "annotation_mode": "str", # For local annotation types
                    "short_name": "str",
                    "description": "str",
                    "parent_id": "str"
                    }
            }
            ...
        ]
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

    As of API version 0.4, when the model version sets a batch size above 1, `files` is a list of
    such lists -- one per resource in the batch -- so a single request covers the whole batch. A
    model that defines `predict_batch(data)` alongside `predict(data)` is handed the groups as they
    are and can batch the work across them; otherwise `predict` is called once per group and sees
    the flat list it expects.

    A multi-frame instance is stored as a series of one virtual instance per frame, but it is sent
    as the single DICOM file it came from, once, whatever the model scope. A model that supports
    multi-frame reads the frames from that file itself and returns a zero-based `frame_number` on
    each output; the platform maps those back to the per-frame instances. An output that omits
    `frame_number` for a multi-frame instance does not identify a frame and will not map.

    The additional `args` dict supply values that may be used in a given run.

    For a file with `content_type='application/dicom'`, `content` is the raw binary data
    representing a DICOM file, and can be loaded using:
    `ds = pydicom.dcmread(BytesIO(file["content"]))`.

    The response body should be the msgpack-serialized binary data of the results:

    [
        {
            "type": "str", # 'NONE', 'ANNOTATION', 'DICOM'
            "study_uid": "str",
            "series_uid": "str",
            "instance_uid": "str",
            "frame_number": "int",
            "class_index": "int",
            "data": {},
            "probability": "float" or "list[dict[str, float]]",
            "note": "str",
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
    if not request.headers["content-type"] == "application/msgpack":
        raise HTTPException(status_code=400)

    if not mdai_model:
        logger.exception(mdai_model_error)
        return _error_response(f"Error initializing model: {mdai_model_error}")

    # Reading and unpacking the request body happens outside the lock, so the next request's upload
    # overlaps with the inference already running rather than queueing behind it.
    try:
        body = await request.body()
        data = await asyncio.to_thread(msgpack.unpackb, body, raw=False)
        del body
        _resolve_input_paths(data.get("files") or [])
    except Exception as e:
        logger.exception(e)
        return _error_response("Error reading input data")

    input_paths = _input_file_paths(data.get("files") or [])
    cancelled = threading.Event()

    # Inference runs one at a time -- there is a single model and, usually, a single GPU -- but it
    # runs in a worker thread. Calling into the model directly from the event loop stalls every
    # other route for the length of the inference, including the readiness probe, which drops the
    # pod out of its service's endpoints for as long as it is doing useful work.
    async with app.state.lock:
        watcher = asyncio.ensure_future(_watch_for_disconnect(request, cancelled))
        try:
            results = await asyncio.to_thread(_predict, data, cancelled)
        except Exception as e:
            logger.exception(e)
            return _error_response(f"Error running model: {traceback.format_exc()}")
        finally:
            watcher.cancel()
            try:
                await watcher
            except asyncio.CancelledError:
                pass
            # The input files have been read by now, whether the model succeeded, failed or was
            # abandoned. Freeing them here rather than only on the success path is what keeps a
            # failing model from filling the node's disk.
            await asyncio.to_thread(_remove_input_files, input_paths)

    if cancelled.is_set():
        # Nobody is waiting for this response. Skip validating and packing a result that cannot be
        # delivered, and say so plainly in the log so an abandoned request is visible as one.
        logger.warning(
            "Client disconnected before inference finished; discarding the result "
            f"({len(input_paths)} input files)."
        )
        return Response(status_code=499, content="")

    try:
        await asyncio.to_thread(output_validator.validate, results)
    except Exception as e:
        logger.exception(e)
        return _error_response(f"Invalid data format returned by model: {e}")

    try:
        resp_content = await asyncio.to_thread(msgpack.packb, results, use_bin_type=True)
        headers = {"Content-Type": "application/msgpack"}
        return Response(content=resp_content, status_code=200, headers=headers)
    except Exception as e:
        logger.exception(e)
        return _error_response("Error writing output data")


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


if __name__ == "__main__":
    try:
        from mdai_deploy import MDAIModel

        mdai_model = MDAIModel()
    except Exception:
        mdai_model_error = traceback.format_exc()

    mdai_model_ready = True

    # A restarted container can come back to a volume still holding the previous process's inputs.
    _clear_data_path()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Ensure inference is run one at a time
    app.state.lock = asyncio.Lock()

    config = Config(app=app, host="0.0.0.0", port=6324, workers=1)
    server = Server(config)

    loop.run_until_complete(server.serve())
