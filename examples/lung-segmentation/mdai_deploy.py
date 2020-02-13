from io import BytesIO
import cv2
import pydicom
import tensorflow as tf
from keras_unet.metrics import iou
from skimage.measure import find_contours
import numpy as np
from preprocess import preprocess_image


class MDAIModel:
    def __init__(self):
        self.model = tf.keras.models.load_model("./lib/lung_segmentation.h5", custom_objects={'iou': iou})

    def predict(self, data):
        input_instances = data["instances"]
        input_args = data["args"]

        results = []

        for instance in input_instances:
            tags = instance["tags"]
            ds = pydicom.dcmread(BytesIO(instance["file"]))
            image = ds.pixel_array
            original_dims = image.shape

            x, offset = preprocess_image(image)
            imgsize = x.shape[1]

            mask  = self.model.predict(x)[0, :, :, 0] > 0.5
            mask = mask.astype(np.uint8)

            # Handle padding and resize
            mask = mask[offset[0] : imgsize-offset[0], offset[1] : imgsize-offset[1]]
            mask = cv2.resize(mask, (original_dims[1], original_dims[0])).astype(np.uint8)

            # Will be a 3D array where each row contains one shape
            vertices = []
            for contour in find_contours(mask, 0):
                vertices.append([[int(v[0]), int(v[1])] for v in contour])

            result = {
                "type": "ANNOTATION",
                "study_uid": tags["StudyInstanceUID"],
                "series_uid": tags["SeriesInstanceUID"],
                "instance_uid": tags["SOPInstanceUID"],
                "frame_number": None,
                "class_index": 0,
                "data": { "vertices": vertices},
           }
            results.append(result)

        return results
