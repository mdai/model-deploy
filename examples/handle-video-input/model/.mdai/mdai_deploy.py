import cv2
import numpy as np
import tempfile
import os


class MDAIModel:
    def __init__(self):
        pass

    def predict(self, data):
        """
        Process input video files and generate annotations.

        This method demonstrates how to handle video input in an MD.ai model deployment.
        It processes each frame of the input video and generates a simple annotation:
        a rectangle that moves from left to right across the video frames.

        Args:
            data (dict): Input data containing files, annotations, label classes, and arguments.

        Returns:
            list: A list of annotation dictionaries for each processed video frame.

        For more details on the schema of `data` and the required output format, see:
        https://github.com/mdai/model-deploy/blob/master/mdai/server.py
        """
        input_files = data["files"]
        output = []

        for input_file in input_files:
            dicom_tags = input_file.get("dicom_tags", {})
            video_content = input_file.get("content")

            if video_content is None:
                continue

            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
                temp_video.write(video_content)
                temp_video_path = temp_video.name

            cap = cv2.VideoCapture(temp_video_path)

            if not cap.isOpened():
                print(f"Error: Could not open video file {temp_video_path}")
                os.unlink(temp_video_path)
                continue

            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            for frame_number in range(frame_count):
                ret, frame = cap.read()
                if not ret:
                    break

                annotation = self._create_annotation(
                    dicom_tags, frame_number, frame_count, frame_width, frame_height
                )
                output.append(annotation)

                print(f"Processing frame {frame_number}")

            cap.release()
            os.unlink(temp_video_path)

        return output

    @staticmethod
    def _create_annotation(
        dicom_tags, frame_number, frame_count, frame_width, frame_height
    ):
        """Create an annotation for a single video frame."""
        return {
            "study_uid": dicom_tags.get("StudyInstanceUID"),
            "series_uid": dicom_tags.get("SeriesInstanceUID"),
            "type": "ANNOTATION",
            "class_index": 0,
            "data": {
                "x": int(frame_number * (frame_width - 100) / (frame_count - 1)),
                "y": int((frame_height - 100) / 2),
                "width": 100,
                "height": 100,
            },
            "video_frame_number": frame_number,
        }
