import numpy as np
from PIL import Image
import cv2

IMAGE_SIZE = 128


def preprocess_image(image):
    image_width = image.shape[1]
    image_height = image.shape[0]

    # resizing and padding
    if image.shape[0] == image.shape[1]:
        resized_shape = (IMAGE_SIZE, IMAGE_SIZE)
        offset = (0, 0)

    # height > width
    elif image.shape[0] > image.shape[1]:
        resized_shape = (IMAGE_SIZE, round(IMAGE_SIZE * image.shape[1] / image.shape[0]))
        offset = (0, (IMAGE_SIZE - resized_shape[1]) // 2)

    else:
        resized_shape = (round(IMAGE_SIZE * image.shape[0] / image.shape[1]), IMAGE_SIZE)
        offset = ((IMAGE_SIZE - resized_shape[0]) // 2, 0)

    resized_shape = (resized_shape[1], resized_shape[0])
    image_resized = cv2.resize(image, resized_shape).astype(np.uint8)

    resized_shape = (resized_shape[1], resized_shape[0])
    image_padded = np.zeros((IMAGE_SIZE, IMAGE_SIZE), dtype=np.uint8)
    image_padded[
        offset[0] : (offset[0] + resized_shape[0]), offset[1] : (offset[1] + resized_shape[1])
    ] = image_resized

    return image_padded[None, :, :, None], offset
