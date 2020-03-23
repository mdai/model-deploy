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
            "probability": [float, type(None)],
            "explanations": [list, type(None)],
        }

        self.data_types = {
            "point": {"x": int, "y": int},
            "box": {"x": int, "y": int, "width": int, "height": int},
            "vertices": {"vertices": list},
        }

        # Dict for mapping function to specific data types. Used for additional checks
        # Can be used to map validation classes later if it needs to be extended
        self.data_validators = {
            "point": None,
            "box": None,
            "vertices": self.validate_data_with_vertices,
        }

    def validate(self, results):
        if type(results) != list:
            raise InvalidFormatException("Expected list, got {}".format(type(results)))
        for result in results:
            self.validate_keys(result)
            self.validate_types(result)
            self.validate_data(result)

    def validate_keys(self, result):
        if result.get("type") not in self.required_keys.keys():
            raise InvalidFormatException("Invalid result type. Got {}".format(result.get("type")))
        for key in self.required_keys[result["type"]]:
            if key not in result:
                raise InvalidFormatException("Key {} not found in model output".format(key))

    def validate_types(self, result):
        for key in result.keys():
            expected_types = (
                self.types[key] if isinstance(self.types[key], list) else [self.types[key]]
            )
            if type(result.get(key)) not in expected_types:
                raise InvalidFormatException(
                    "Incorrect type for key {} in model output. Expected {}, got {}".format(
                        key, self.types[key], result.get(key)
                    )
                )

    def validate_data(self, result):
        if result.get("data") is None:
            return
        data_format = None
        for data_type in self.data_types.keys():
            if set(result["data"].keys()) == set(self.data_types[data_type].keys()):
                data_format = data_type

        if data_format is None:
            raise InvalidFormatException("data field does not conform to any known format")

        for key in result["data"].keys():
            if not isinstance(result["data"][key], self.data_types[data_format][key]):
                raise InvalidFormatException(
                    "Invalid data type for {} expected {}".format(
                        type(result["data"][key]), self.data_types[data_format][key]
                    )
                )

        if self.data_validators[data_format] is not None:
            self.data_validators[data_format](result["data"])

    def validate_data_with_vertices(self, data):
        VERTEX_TYPE = int
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
        if not type(vertex[0]) is VERTEX_TYPE or not type(vertex[1]) is VERTEX_TYPE:
            raise InvalidFormatException(
                "Invalid vertex data type. Got {} Expected {}".format(
                    [type(vertex[0]), type(vertex[1])], VERTEX_TYPE
                )
            )
