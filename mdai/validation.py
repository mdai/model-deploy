class InvalidFormatException(Exception):
    pass


class OutputValidator:
    def __init__(self):
        self.required_keys = {
            "NONE": ["study_uid"],
            "ANNOTATION": ["study_uid", "class_index"],
            "IMAGE": ["study_uid", "class_index", "images"],
            "DICOM": ["study_uid", "class_index", "images"],
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
            "note": [str, dict, type(None)],
            "images": [list, type(None)],
            "image_output_tags": [dict, type(None)],
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
            "mask": self.validate_data_with_mask,
        }

        self.note_dict_types = {"input": str, "output": str}

        self.image_output_tags_types = {
            "PatientID": str,
            "StudyInstanceUID": str,
            "SeriesInstanceUID": str,
        }

    def validate(self, outputs):
        if not isinstance(outputs, list):
            raise InvalidFormatException("Expected list, got {}".format(type(outputs)))
        for output in outputs:
            self.validate_keys(output)
            self.validate_types(output)
            self.validate_data(output)
            self.validate_note(output)
            self.validate_image_output_tags(output)

    def validate_keys(self, output):
        if output.get("type") not in self.required_keys.keys():
            raise InvalidFormatException("Invalid output type. Got {}".format(output.get("type")))
        for key in self.required_keys[output["type"]]:
            if key not in output:
                raise InvalidFormatException("Key '{}' not found in model output".format(key))

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
            raise InvalidFormatException(
                "Model output data field does not conform to any known format."
            )

        for key in output["data"].keys():
            if not isinstance(output["data"][key], self.data_types[data_format][key]):
                raise InvalidFormatException(
                    "Invalid type for key '{}' in data. Expected {}, got {}".format(
                        key, self.data_types[data_format][key], type(output["data"][key])
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

        if not isinstance(vertices[0], list):
            raise InvalidFormatException("Vertices needs to be a 2D array")

        if len(vertices[0]) != VERTEX_DIMENSIONS:
            raise InvalidFormatException(
                "Each vertex needs to have only 2 values [x, y] got {} values.".format(
                    len(vertices[0])
                )
            )

        vertex = vertices[0]
        if type(vertex[0]) not in VERTEX_TYPE or type(vertex[1]) not in VERTEX_TYPE:
            raise InvalidFormatException(
                "Invalid vertex data type. Got {} Expected {}".format(
                    [type(vertex[0]), type(vertex[1])], VERTEX_TYPE
                )
            )

    def validate_data_with_mask(self, data):
        MASK_TYPE = [int, float]

        mask = data.get("mask")
        if len(mask) == 0:
            return

        if not isinstance(mask[0], list):
            raise InvalidFormatException(
                "Mask needs to be returned as a 2D python list.\nNumpy arrays can be converted to lists using the .tolist() method"
            )

        if len(mask[0]) == 0:
            return

        mask_value = mask[0][0]
        if type(mask_value) not in MASK_TYPE:
            raise InvalidFormatException(
                "Invalid mask data type. Got {} Expected {}".format(type(mask_value), MASK_TYPE)
            )

    def validate_note(self, output):
        note = output.get("note")
        if not note:
            return

        if isinstance(note, dict):
            for key in note.keys():
                if key not in self.note_dict_types.keys():
                    raise InvalidFormatException(
                        "Invalid key for output note dict. Got '{}' Expected {}".format(
                            key, list(self.note_dict_types.keys())
                        )
                    )
                value = note.get(key)
                if not isinstance(value, self.note_dict_types[key]):
                    raise InvalidFormatException(
                        "Invalid value type for note dict key '{}'. Got '{}' Expected {}".format(
                            key, type(value), self.note_dict_types[key]
                        )
                    )

    def validate_image_output_tags(self, output):
        image_output_tags = output.get("image_output_tags")
        if not image_output_tags:
            return

        for key in image_output_tags.keys():
            if key not in self.image_output_tags_types:
                raise InvalidFormatException(
                    "Invalid key for image_output_tags. Got '{}', expected values include {}".format(
                        key, list(self.image_output_tags_types.keys())
                    )
                )

            if not isinstance(image_output_tags[key], self.image_output_tags_types[key]):
                raise InvalidFormatException(
                    "Invalid type for image_output_tags[{}]. Got '{}' expected {}".format(
                        key, type(image_output_tags[key]), self.image_output_tags_types[key]
                    )
                )
