FREEFORM = "freeform"
LOCATION = "location"
BOX = "box"
VERTEX_DIMENSIONS = 2


class InvalidFormatException(Exception):
    pass


class OutputValidator:
    def __init__(self):
        # Dict for checking types, uses list if type can be one of multiple types
        self.types = {
            "type": str,
            "study_uid": str,
            "series_uid": str,
            "instance_uid": str,
            "frame_number": [int, type(None)],
            "class_index": int,
            "data": [dict, type(None)],
            "probability": [float, type(None)],
            "explanations": list,
        }

        self.data_types = {
            LOCATION: {"x": int, "y": int},
            FREEFORM: {"vertices": list},
            BOX: {"x": int, "y": int, "width": int, "height": int},
        }

        # Dict for mapping function to specific data types. Used for additional checks
        # Can be used to map validation classes later if it needs to be extended
        self.data_validators = {FREEFORM: self.validate_freeform, LOCATION: None, BOX: None}

    def validate(self, output):
        if type(output) != list:
            raise InvalidFormatException("Expected list, got {}".format(type(output)))
        for instance in output:
            self.validate_keys(instance)
            self.validate_types(instance)
            self.validate_data(instance)

    def validate_keys(self, instance):
        for key in self.types.keys():
            if key not in instance:
                raise InvalidFormatException("Key {} not found in model output".format(key))

    def validate_types(self, instance):
        for key in self.types.keys():
            expected_types = (
                self.types[key] if isinstance(self.types[key], list) else [self.types[key]]
            )
            if type(instance[key]) not in expected_types:
                raise InvalidFormatException(
                    "Incorrect type for key {} in model output. Expected {}, got {}".format(
                        key, self.types[key], instance[key]
                    )
                )

    def validate_data(self, output):
        if output["data"] is None:
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

    def validate_freeform(self, data):
        VERTEX_TYPE = int
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
