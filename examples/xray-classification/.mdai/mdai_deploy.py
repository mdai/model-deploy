import os
from io import BytesIO
import cv2
import pydicom
import tensorflow as tf
from PIL import Image
from tf_explain.core import GradCAM, SmoothGrad

from preprocess import preprocess_image


class MDAIModel:
    def __init__(self):
        modelpath = os.path.join(os.path.dirname(__file__), "..", "model", "model.h5")
        self.model = tf.keras.models.load_model(modelpath)

    def predict(self, data):
        """
        The input data has the following schema:

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

        The results returned by this function should have the following schema:

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
        input_instances = data["instances"]
        input_args = data["args"]

        results = []

        for instance in input_instances:
            tags = instance["tags"]
            ds = pydicom.dcmread(BytesIO(instance["file"]))
            image = ds.pixel_array
            x = preprocess_image(image)

            y_prob = self.model.predict(x)
            y_classes = y_prob.argmax(axis=-1)

            class_index = y_classes[0]
            probability = y_prob[0][class_index]

            gradcam = GradCAM()
            gradcam_output = gradcam.explain(
                validation_data=(x, None),
                model=self.model,
                layer_name="conv_pw_13_relu",
                class_index=class_index,
                colormap=cv2.COLORMAP_TURBO,
            )
            gradcam_output_buffer = BytesIO()
            Image.fromarray(gradcam_output).save(gradcam_output_buffer, format="PNG")

            smoothgrad = SmoothGrad()
            smoothgrad_output = smoothgrad.explain(
                validation_data=(x, None), model=self.model, class_index=class_index
            )
            smoothgrad_output_buffer = BytesIO()
            Image.fromarray(smoothgrad_output).save(smoothgrad_output_buffer, format="PNG")

            result = {
                "type": "ANNOTATION",
                "study_uid": tags["StudyInstanceUID"],
                "series_uid": tags["SeriesInstanceUID"],
                "instance_uid": tags["SOPInstanceUID"],
                "class_index": int(class_index),
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
            results.append(result)

        return results
