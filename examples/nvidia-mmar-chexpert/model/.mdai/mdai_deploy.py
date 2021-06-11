import os
from io import BytesIO
import pydicom
import json
import cv2
import subprocess
import pandas


class MDAIModel:
    def __init__(self):
        self.root_path = "/workspace/classificationfl_chexpert_v4"
        self.data_path = "/workspace/data"

    def predict(self, data):
        """
        See https://github.com/mdai/model-deploy/blob/master/mdai/server.py for details on the
        schema of `data` and the required schema of the outputs returned by this function.
        """
        input_files = data["files"]
        outputs = []
        for file in input_files:
            if file["content_type"] != "application/dicom":
                continue

            # Load dicom image
            ds = pydicom.dcmread(BytesIO(file["content"]))
            img = ds.pixel_array

            # Save dicom images as jpg in the data directory
            img_path = os.path.join(self.data_path, ds.SOPInstanceUID + ".jpg")
            cv2.imwrite(img_path, img)

            # Edit dataset_0.json file with new data path
            with open(
                os.path.join(self.root_path, "config", "dataset_0.json"), "r"
            ) as f:
                dataset_json = json.load(f)

            dataset_json["validation"] = [{"image": img_path}]

            with open(
                os.path.join(self.root_path, "config", "dataset_0.json"), "w"
            ) as f:
                json.dump(dataset_json, f)

            # Run model
            subprocess.run(
                ["bash", os.path.join(self.root_path, "commands", "infer.sh")]
            )

            # Load predictions
            results = pandas.read_csv(
                os.path.join(self.root_path, "eval", "preds_model.csv"), header=None
            )

            # Return outputs to interface
            count = 0
            for i in range(1, len(results.columns)):
                prob = results[i].values[0]
                if prob >= 0.5:
                    outputs.append(
                        {
                            "type": "ANNOTATION",
                            "study_uid": str(ds.StudyInstanceUID),
                            "series_uid": str(ds.SeriesInstanceUID),
                            "instance_uid": str(ds.SOPInstanceUID),
                            "class_index": i - 1,
                            "probability": float(prob),
                        }
                    )
                    count += 1

            if count == 0:
                outputs.append(
                    {
                        "type": "NONE",
                        "study_uid": str(ds.StudyInstanceUID),
                        "series_uid": str(ds.SeriesInstanceUID),
                        "instance_uid": str(ds.SOPInstanceUID),
                    }
                )
        return outputs
