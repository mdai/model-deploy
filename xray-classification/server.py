__version__ = "0.1.1"


import logging
from io import BytesIO
import cv2
import msgpack
import numpy as np
import tensorflow as tf
from flask import Flask, Response, abort, request
from PIL import Image
from tf_explain.core import GradCAM, SmoothGrad
from waitress import serve

app = Flask(__name__)
model = None

config = {"input_shape": (224, 224, 3)}


def load_model():
    global model
    model = tf.keras.models.load_model("./model.h5")


def prepare_input(image):
    # convert grayscale to RGB
    if len(image.shape) != 3 or image.shape[2] != 3:
        image = np.stack((image,) * 3, -1)

    # rescale to [0, 255]
    max_pixel_value = np.amax(image)
    min_pixel_value = np.amin(image)
    if max_pixel_value >= 255:
        pixel_range = max(1, np.abs(max_pixel_value - min_pixel_value))
        image = image.astype(np.float32) / pixel_range * 255
        image = image.astype(np.uint8)

    # resize to input_shape
    image = Image.fromarray(image)
    image = image.resize(config["input_shape"][0:2])

    # create input batch
    x = np.empty((1, *config["input_shape"]))
    x[0, :] = image

    return x


def predict(x):
    y_prob = model.predict(x)
    y_classes = y_prob.argmax(axis=-1)

    class_index = y_classes[0]
    probability = y_prob[0][class_index]

    gradcam = GradCAM()
    gradcam_output = gradcam.explain(
        validation_data=(x, None),
        model=model,
        layer_name="conv_pw_13_relu",
        class_index=class_index,
        colormap=cv2.COLORMAP_TURBO,
    )
    gradcam_output_buffer = BytesIO()
    Image.fromarray(gradcam_output).save(gradcam_output_buffer, format="PNG")

    smoothgrad = SmoothGrad()
    smoothgrad_output = smoothgrad.explain(
        validation_data=(x, None), model=model, class_index=class_index
    )
    smoothgrad_output_buffer = BytesIO()
    Image.fromarray(smoothgrad_output).save(smoothgrad_output_buffer, format="PNG")

    result = {
        "class_index": int(class_index),
        "data": None,
        "probability": float(probability),
        "explanations": [
            {
                "name": "Grad-CAM",
                "description": "Visualize how parts of the image affects neural network’s output by looking into the activation maps. From _Grad-CAM: Visual Explanations from Deep Networks via Gradient-based Localization_ (https://arxiv.org/abs/1610.02391)",
                "content": gradcam_output_buffer.getvalue(),
                "content_type": "image/png",
            },
            {
                "name": "SmoothGrad",
                "description": "Visualize stabilized gradients on the inputs towards the decision. From _SmoothGrad: removing noise by adding noise_ (https://arxiv.org/abs/1706.03825)",
                "content": smoothgrad_output_buffer.getvalue(),
                "content_type": "image/png",
            },
        ],
    }
    return result


@app.route("/inference", methods=["POST"])
def inference():
    """
    Route for model inference.

    The POST body is msgpack-serialized binary data with the follow schema:

    {
        "instances": [
            {
                "pixel_array": "bytes"
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

    The image bytes is the raw binary data representing a numpy saved file, and can be loaded using
    `np.load()`.

    The response body should be the msgpack-serialized binary data of the results:

    [
        {
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
    """
    if not request.content_type == "application/msgpack":
        abort(400)

    data = msgpack.unpackb(request.get_data(), raw=False)
    input_instances = data["instances"]
    input_args = data["args"]

    results = []

    for instance in input_instances:
        try:
            tags = instance["tags"]
            image = np.load(BytesIO(instance["pixel_array"]))
            result = predict(prepare_input(image))
            result["study_uid"] = tags["StudyInstanceUID"]
            result["series_uid"] = tags["SeriesInstanceUID"]
            result["instance_uid"] = tags["SOPInstanceUID"]
            result["frame_number"] = None
            results.append(result)
        except Exception as e:
            logging.exception(e)
            abort(500)

    resp = Response(msgpack.packb(results, use_bin_type=True))
    resp.headers["Content-Type"] = "application/msgpack"
    return resp


@app.route("/healthz", methods=["GET"])
def healthz():
    return "", 200


if __name__ == "__main__":
    load_model()
    serve(app, listen="*:6324")
