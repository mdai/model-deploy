import os
from os import listdir
import pydicom
from io import BytesIO
import msgpack

PATH_DELIMITER = "/"
DCM_EXTENSION = ".dcm"


def is_folder(path):
    return os.path.isdir(path)


def is_dicom(path):
    return path.endswith(DCM_EXTENSION)


def file_search(path):
    if not is_folder(path):
        if is_dicom(path):
            return [path]
        else:
            return []

    file_paths = []
    folder_queue = [path]
    while len(folder_queue) != 0:
        current_folder = folder_queue.pop(0)

        for path in listdir(current_folder):
            current_path = current_folder + PATH_DELIMITER + path
            if is_folder(current_path):
                folder_queue.append(current_path)
            elif is_dicom(current_path):
                file_paths.append(current_path)

    return file_paths


def process_data(path):
    file_paths = file_search(path)
    result = {}
    result["instances"] = []
    result["args"] = {}
    for path in file_paths:
        result["instances"].append(process_file(path))
    return msgpack.packb(result)


def process_file(path):
    with open(path, "rb") as fp:
        instance = {}
        file_content = fp.read()
        dicom_content = pydicom.read_file(BytesIO(file_content))

        tags = {}
        tags["StudyInstanceUID"] = dicom_content.StudyInstanceUID
        tags["SeriesInstanceUID"] = dicom_content.SeriesInstanceUID
        tags["SOPInstanceUID"] = dicom_content.SOPInstanceUID
        instance["tags"] = tags
        instance["file"] = file_content

        return instance
