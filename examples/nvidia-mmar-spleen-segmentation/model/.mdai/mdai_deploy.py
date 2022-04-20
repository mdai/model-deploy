import os
from io import BytesIO
import pydicom
import json
import subprocess
import dicom2nifti
import nibabel
import numpy as np


class MDAIModel:
    def __init__(self):
        # Set MMAR root folder name
        self.root_path = os.path.join("/workspace")
        self.config_path = os.path.join(self.root_path, "config")
        self.env_file = os.path.join(self.config_path, "environment.json")

        # Load env file
        with open(os.path.join(self.env_file), "r") as f:
            env_json = json.load(f)

        # Create /workspace/data folder if not exists
        self.data_path = "/workspace/data"
        if not os.path.exists(self.data_path):
            os.mkdir(self.data_path)

        # Create /workspace/eval folder if not exists
        self.eval_path = "/workspace/eval"
        if not os.path.exists(self.eval_path):
            os.mkdir(self.eval_path)

        # Set DATA_ROOT and MMAR_EVAL_OUTPUT_PATH in environment.json
        env_json["DATA_ROOT"] = self.data_path
        env_json["MMAR_EVAL_OUTPUT_PATH"] = self.eval_path

        self.out_classes = env_json["OUTPUT_CHANNELS"]
        self.data_key = env_json["INFER_DATALIST_KEY"]
        self.dataset_json_path = os.path.join(self.root_path, env_json["DATASET_JSON"])

        with open(os.path.join(self.env_file), "w") as f:
            json.dump(env_json, f)

        # Change batch size to 1 in config_inference.json
        self.config_inf = os.path.join(self.config_path, "config_inference.json")
        with open(os.path.join(self.config_inf), "r") as f:
            inf_json = json.load(f)

        inf_json["dataloader"]["args"]["batch_size"] = 1
        inf_json["dataloader"]["args"]["num_workers"] = 0
        inf_json["inferer"]["sw_batch_size"] = 1

        with open(os.path.join(self.config_inf), "w") as f:
            json.dump(inf_json, f)

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
        positions = [ds.ImagePositionPatient for ds in dicom_files]
        reverse = (
            False if positions[0][0] < 0 or positions[0][1] < 0 or positions[0][2] < 0 else True
        )

        # Flip pixel data to get LAS orientation
        if reverse:
            for i, ds in enumerate(dicom_files):
                ds.ImagePositionPatient = positions[len(positions) - i - 1]

        # Convert dicom to nifti
        file_name = dicom_files[0].SeriesInstanceUID
        output_file = os.path.join(self.data_path, file_name + ".nii.gz")
        nifti_file = dicom2nifti.convert_dicom.dicom_array_to_nifti(
            dicom_files,
            output_file=output_file,
            reorient_nifti=True,
        )

        # Edit dataset_test.json file with new data path
        with open(self.dataset_json_path, "r") as f:
            dataset_json = json.load(f)

        first_data_entry = dataset_json[self.data_key][0]
        if type(first_data_entry) == str:
            dataset_json[self.data_key] = [nifti_file["NII_FILE"]]
        elif type(first_data_entry) == dict:
            if "label" in first_data_entry:
                dataset_json[self.data_key] = [{"image": nifti_file["NII_FILE"], "label": None}]
            else:
                dataset_json[self.data_key] = [{"image": nifti_file["NII_FILE"]}]

        with open(self.dataset_json_path, "w") as f:
            json.dump(dataset_json, f)

        # Run model
        subprocess.run(["bash", os.path.join(self.root_path, "commands", "infer.sh")])

        # Load predictions
        result = nibabel.load(
            os.path.join(
                self.eval_path,
                file_name,
                file_name + "_trans.nii.gz",
            )
        ).get_fdata()

        # Return outputs to interface
        result = np.transpose(result, (2, 0, 1))
        if reverse:
            result = result[::-1]

        for ds, seg_mask in zip(dicom_files, result):
            masks = [
                (np.rot90(seg_mask == t + 1), t)
                for t in range(self.out_classes - 1)
                if np.sum(seg_mask == t + 1) > 0
            ]
            if masks:
                for mask in masks:
                    outputs.append(
                        {
                            "type": "ANNOTATION",
                            "study_uid": str(ds.StudyInstanceUID),
                            "series_uid": str(ds.SeriesInstanceUID),
                            "instance_uid": str(ds.SOPInstanceUID),
                            "class_index": mask[1],
                            "data": {"mask": mask[0].tolist()},
                        }
                    )
            else:
                # Return default NONE output is there is no prediction
                outputs.append(
                    {
                        "type": "NONE",
                        "study_uid": str(ds.StudyInstanceUID),
                        "series_uid": str(ds.SeriesInstanceUID),
                        "instance_uid": str(ds.SOPInstanceUID),
                    }
                )
        return outputs
