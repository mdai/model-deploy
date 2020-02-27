from output_validator import OutputValidator
from output_validator import InvalidFormatException
import pytest


class TestOutputValidator:
    def setup(self):
        self.output_validator = OutputValidator()

        self.sample_output = {
            "type": "ANNOTATION",
            "study_uid": "1.2.276.0.7230010.3.1.2.940180736.574.1534894495.485465",
            "series_uid": "1.2.276.0.7230010.3.1.3.940180736.574.1534894495.485464",
            "instance_uid": "1.2.276.0.7230010.3.1.4.940180736.574.1534894495.485466.dcm",
            "frame_number": None,
            "class_index": 0,
            "probability": None,
            "data": None,
            "explanations": [],
        }

    def test_missing(self):
        output = dict(self.sample_output)
        for key in self.sample_output.keys():
            value = output.pop(key, None)
            with pytest.raises(InvalidFormatException):
                self.output_validator.validate([output])
            output[key] = value

    def test_valid_types(self):
        valid_values = {
            "frame_number": [1],
            "probability": [0.5],
            "data": [
                {"vertices": [[1, 2], [3, 4]]},
                {"x": 35, "y": 45},
                {"x": 44, "y": 55, "width": 20, "height": 30},
            ],
        }
        output = dict(self.sample_output)

        for key in valid_values:
            for value in valid_values[key]:
                prev_value = output[key]
                output[key] = value
                self.output_validator.validate([output])
                output[key] = prev_value

    def test_invaid_types(self):
        output = dict(self.sample_output)
        invalid_values = {
            "type": [1, 0.1, None],
            "study_uid": [1, 0.1, None],
            "frame_number": [0.1, "1"],
            "class_index": [5.5, "5", None],
            "probability": ["5"],
            "data": [[], 1, "50"],
            "explanations": [None, {}],
        }
        for key in invalid_values:
            for value in invalid_values[key]:
                prev_value = output[key]
                output[key] = value
                print(key, value)
                with pytest.raises(InvalidFormatException):
                    self.output_validator.validate([output])
                output[key] = prev_value

    def test_data_field(self):
        invalid_data_fields = [
            {"vertex": [[1, 2], [3, 4]]},
            {"vetices": [1, 2, 3, 4]},
            {"vertices": [[1, 2, 3], [4, 5]]},
            {"vertices": [[0.1, 0.2], [0.3, 0.4]]},
            {"x": 50, "y": 50, "z": 50},
            {"x": 0.1, "y": 0.5},
            {"x": 50, "y": 50, "width": 50.5, "height": 50.5},
        ]

        output = dict(self.sample_output)
        key = "data"

        for data_field in invalid_data_fields:
            print(data_field)
            prev_value = output[key]
            output[key] = data_field
            with pytest.raises(InvalidFormatException):
                self.output_validator.validate([output])
            output[key] = prev_value
