class InvalidFormatException(Exception):
    pass


class OutputValidator:
    def __init__(self):
        self.required_keys = {
            "NONE": ["study_uid"],
            "ANNOTATION": ["study_uid", "class_index"],
            "IMAGE": ["study_uid"],
            "DICOM": ["study_uid"],
            "TEXT": ["study_uid"],
        }

        # Dict for checking types, uses list if type can be one of multiple types
        self.types = {
            "type": str,
            "study_uid": str,
            "series_uid": [str, type(None)],
            "instance_uid": [str, type(None)],
            "frame_number": [int, type(None)],
            "class_index": int,
            "data": [dict, type(None)],
            "probability": [float, list, type(None)],
            "explanations": [list, type(None)],
        }

        self.data_types = {
            "point": {"x": int, "y": int},
            "box": {"x": int, "y": int, "width": int, "height": int},
            "vertices": {"vertices": list},
            "mask": {"mask": list},
        }

        # Dict for mapping function to specific data types. Used for additional checks
        # Can be used to map validation classes later if it needs to be extended
        self.data_validators = {
            "point": None,
            "box": None,
            "vertices": self.validate_data_with_vertices,
            "mask": None,
        }

    def validate(self, outputs):
        if type(outputs) != list:
            raise InvalidFormatException("Expected list, got {}".format(type(outputs)))
        for output in outputs:
            self.validate_keys(output)
            self.validate_types(output)
            self.validate_data(output)

    def validate_keys(self, output):
        if output.get("type") not in self.required_keys.keys():
            raise InvalidFormatException("Invalid output type. Got {}".format(output.get("type")))
        for key in self.required_keys[output["type"]]:
            if key not in output:
                raise InvalidFormatException("Key {} not found in model output".format(key))

    def validate_types(self, output):
        for key in output.keys():
            expected_types = (
                self.types[key] if isinstance(self.types[key], list) else [self.types[key]]
            )
            if type(output.get(key)) not in expected_types:
                raise InvalidFormatException(
                    "Incorrect type for key {} in model output. Expected {}, got {}".format(
                        key, self.types[key], output.get(key)
                    )
                )

    def validate_data(self, output):
        if output.get("data") is None:
            return
        data_format = None
        for data_type in self.data_types.keys():
            if set(output["data"].keys()) == set(self.data_types[data_type].keys()):
                data_format = data_type

        if data_format is None:
            raise InvalidFormatException("data field does not conform to any known format")

        for key in output["data"].keys():
            if not isinstance(output["data"][key], self.data_types[data_format][key]):
                raise InvalidFormatException(
                    "Invalid data type for {} expected {}".format(
                        type(output["data"][key]), self.data_types[data_format][key]
                    )
                )

        if self.data_validators[data_format] is not None:
            self.data_validators[data_format](output["data"])

    def validate_data_with_vertices(self, data):
        VERTEX_TYPE = [int, float]
        VERTEX_DIMENSIONS = 2

        vertices = data["vertices"]
        if len(vertices) == 0:
            return

        if type(vertices[0]) != list:
            raise InvalidFormatException("Vertices needs to be a 2D array")

        if len(vertices[0]) != VERTEX_DIMENSIONS:
            raise InvalidFormatException(
                "Each vertex needs to have only 2 values [x, y] got {}".format(len(vertices[0]))
            )

        vertex = vertices[0]
        if not type(vertex[0]) in VERTEX_TYPE or not type(vertex[1]) in VERTEX_TYPE:
            raise InvalidFormatException(
                "Invalid vertex data type. Got {} Expected {}".format(
                    [type(vertex[0]), type(vertex[1])], VERTEX_TYPE
                )
            )
