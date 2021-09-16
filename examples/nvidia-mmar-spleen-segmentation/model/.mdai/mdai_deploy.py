import os
from io import BytesIO
import pydicom
import json
import subprocess
import pandas
import dicom2nifti
import nibabel
import numpy as np


class MDAIModel:
    def __init__(self):
        self.root_path = "/workspace/clara_pt_spleen_ct_segmentation_1"
        self.data_path = "/workspace/data"
        self.eval_path = "/workspace/eval"

    def predict(self, data):
        """
        See https://github.com/mdai/model-deploy/blob/master/mdai/server.py for details on the
        schema of `data` and the required schema of the outputs returned by this function.
        """
        input_files = data["files"]
        outputs = []
        dicom_files = []
        for file in input_files:
            if file["content_type"] != "application/dicom":
                continue

            # Load dicom image
            dicom_files.append(pydicom.dcmread(BytesIO(file["content"])))

        dicom_files = dicom2nifti.common.sort_dicoms(dicom_files)

        # Flip pixel data to get LAS orientation
        for ds in dicom_files:
            arr = np.flip(ds.pixel_array, 1)
            ds.PixelData = arr.tobytes()

        # Convert dicom to nifti
        file_name = dicom_files[0].SeriesInstanceUID
        output_file = os.path.join(self.data_path, file_name + ".nii.gz")
        nifti_file = dicom2nifti.convert_dicom.dicom_array_to_nifti(
            dicom_files, output_file=output_file, reorient_nifti=True,
        )

        # Edit dataset_test.json file with new data path
        with open(os.path.join(self.data_path, "dataset_test.json"), "r") as f:
            dataset_json = json.load(f)

        dataset_json["test"] = [nifti_file["NII_FILE"]]

        with open(os.path.join(self.data_path, "dataset_test.json"), "w") as f:
            json.dump(dataset_json, f)

        # Run model
        subprocess.run(["bash", os.path.join(self.root_path, "commands", "infer.sh")])

        # Load predictions
        result = nibabel.load(
            os.path.join(self.eval_path, file_name, file_name + "_seg.nii.gz",)
        ).get_fdata()

        # Return outputs to interface
        for ds, mask in zip(dicom_files, np.transpose(result, (2, 0, 1))):
            if np.sum(mask) > 0:
                mask = np.flip(np.rot90(mask), axis=1)
                outputs.append(
                    {
                        "type": "ANNOTATION",
                        "study_uid": str(ds.StudyInstanceUID),
                        "series_uid": str(ds.SeriesInstanceUID),
                        "instance_uid": str(ds.SOPInstanceUID),
                        "class_index": 0,
                        "data": {"mask": mask.tolist()},
                    }
                )

            else:
                outputs.append(
                    {
                        "type": "NONE",
                        "study_uid": str(ds.StudyInstanceUID),
                        "series_uid": str(ds.SeriesInstanceUID),
                        "instance_uid": str(ds.SOPInstanceUID),
                    }
                )
        return outputs
