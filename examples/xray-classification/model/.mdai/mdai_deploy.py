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
        modelpath = os.path.join(os.path.dirname(__file__), "../xray-classficiation-model.h5")
        self.model = tf.keras.models.load_model(modelpath)

    def predict(self, data):
        """
        See https://github.com/mdai/model-deploy/blob/master/mdai/server.py for details on the
        schema of `data` and the required schema of the outputs returned by this function.
        """
        input_files = data["files"]
        input_annotations = data["annotations"]
        input_args = data["args"]

        outputs = []

        for file in input_files:
            if file["content_type"] != "application/dicom":
                continue

            ds = pydicom.dcmread(BytesIO(file["content"]))
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

            output = {
                "type": "ANNOTATION",
                "study_uid": str(ds.StudyInstanceUID),
                "series_uid": str(ds.SeriesInstanceUID),
                "instance_uid": str(ds.SOPInstanceUID),
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
            outputs.append(output)

        return outputs
