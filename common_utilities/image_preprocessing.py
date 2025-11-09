#!/usr/bin/env python3.10


from typing import Union,List
import cv2
from PIL import Image
import numpy as np
import base64
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
def crop_image_bbox(
    image: Union[np.ndarray, cv2.typing.MatLike],
    face_bbox: List[int],
    box_size: int = 280,
) -> Image.Image:
    """
    Crops an area of the image centered on the face bounding box, using a specified square box size.
    The bounding box is defined by its top-left and bottom-right corners.

    Parameters:
    - image: The input image (numpy array).
    - bbox: A tuple or list (x1, y1, x2, y2) representing the bounding box corners of the face.
    - box_size: The size (width and height) of the square box for cropping.

    Returns:
    - Cropped image (numpy array) of the specified square box size centered on the face bbox.
    """
    if not face_bbox or len(face_bbox) != 4:
        return image

    height, width = image.shape[:2]
    x1, y1, x2, y2 = face_bbox
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    half = box_size // 2

    x_start = cx - half
    y_start = cy - half
    x_end = x_start + box_size
    y_end = y_start + box_size

    if x_start < 0:
        x_end -= x_start
        x_start = 0
    if y_start < 0:
        y_end -= y_start
        y_start = 0
    if x_end > width:
        shift = x_end - width
        x_start = max(0, x_start - shift)
        x_end = width
    if y_end > height:
        shift = y_end - height
        y_start = max(0, y_start - shift)
        y_end = height

    x_start = max(0, x_start)
    y_start = max(0, y_start)
    x_end = min(width, x_end)
    y_end = min(height, y_end)

    cropped_image = image[y_start:y_end, x_start:x_end]

    if cropped_image.size == 0:
        return cropped_image

    crop_h, crop_w = cropped_image.shape[:2]
    pad_top = pad_bottom = pad_left = pad_right = 0
    if crop_h < box_size:
        missing = box_size - crop_h
        pad_top = missing // 2
        pad_bottom = missing - pad_top
    if crop_w < box_size:
        missing = box_size - crop_w
        pad_left = missing // 2
        pad_right = missing - pad_left

    if any((pad_top, pad_bottom, pad_left, pad_right)):
        cropped_image = cv2.copyMakeBorder(
            cropped_image,
            pad_top,
            pad_bottom,
            pad_left,
            pad_right,
            borderType=cv2.BORDER_REFLECT_101,
        )

    if cropped_image.shape[0] != box_size or cropped_image.shape[1] != box_size:
        cropped_image = cv2.resize(
            cropped_image, (box_size, box_size), interpolation=cv2.INTER_LINEAR
        )

    return cropped_image
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
def crop_image_center(frame,crop_width=None,crop_height=None):
    # Get the frame dimensions
    frame_height, frame_width = frame.shape[:2]
    if(not crop_width):
        crop_width=frame_width
    if(not crop_height):
        crop_height=frame_width
    # Calculate the center of the frame
    center_x, center_y = frame_width // 2, frame_height // 2
    # Calculate the top-left and bottom-right points for the crop
    x1 = max(0, center_x - crop_width // 2)
    y1 = max(0, center_y - crop_height // 2)
    x2 = min(frame_width, center_x + crop_width // 2)
    y2 = min(frame_height, center_y + crop_height // 2)
    # Crop the frame
    cropped_frame = frame[y1:y2, x1:x2]
    return cropped_frame
#//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
def encoded64image2cv2(ImageBase64:str)->cv2.Mat:
    if  ImageBase64 is None:
        return None
    image_decode = base64.b64decode(ImageBase64)
    np_arr = np.frombuffer(image_decode, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return image
