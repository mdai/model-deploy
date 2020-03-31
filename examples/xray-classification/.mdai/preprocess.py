import numpy as np
from PIL import Image

INPUT_SHAPE = (224, 224, 3)


def preprocess_image(image):
    # convert grayscale to RGB
    if len(image.shape) != 3 or image.shape[2] != 3:
        image = np.stack((image,) * 3, -1)

    # rescale to [0, 255]
    max_pixel_value = np.amax(image)
    min_pixel_value = np.amin(image)
    if max_pixel_value >= 255:
        pixel_range = max(1, np.abs(max_pixel_value - min_pixel_value))
        image = image.astype(np.float32) / pixel_range * 255
        image = image.astype(np.uint8)

    # resize to input_shape
    image = Image.fromarray(image)
    image = image.resize(INPUT_SHAPE[0:2])

    # create input batch
    x = np.empty((1, *INPUT_SHAPE))
    x[0, :] = image

    return x
