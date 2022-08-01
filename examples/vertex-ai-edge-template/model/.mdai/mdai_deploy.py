import os
from io import BytesIO
import numpy as np
import tensorflow as tf


class MDAIModel:
    def __init__(self):
        # Load vertex AI saved model
        modelpath = os.path.dirname(os.path.dirname(__file__))
        model = tf.saved_model.load(modelpath)
        self.model = model.signatures["serving_default"]

    def predict(self, data):
        input_files = data["files"]
        outputs = []

        for file in input_files:
            # Ignore images that are not JPEG/PNG
            if file["content_type"] not in ["image/jpeg", "image/png"]:
                continue

            # DICOM UID mapping
            uids = file["content_uids"]

            # Load JPEG/PNG image
            image = BytesIO(file["content"]).getvalue()

            # Run inference
            prediction = self.model(
                image_bytes=tf.convert_to_tensor([image]),
                key=tf.convert_to_tensor([uids["SOPInstanceUID"]]),
            )
            probabilities = prediction["scores"].numpy()[0]

            # For binary and multiclass classification, we return the index
            # having the maximum probability. This can be changed to a list
            # of indices in case of multilabel classification.
            class_index = int(np.argmax(probabilities))

            outputs.append(
                {
                    "type": "ANNOTATION",
                    "study_uid": uids["StudyInstanceUID"],
                    "series_uid": uids["SeriesInstanceUID"],
                    "instance_uid": uids["SOPInstanceUID"],
                    "class_index": class_index,
                    "probability": [
                        {"class_index": i, "probability": float(j)}
                        for i, j in enumerate(probabilities)
                    ],
                }
            )

        return outputs
