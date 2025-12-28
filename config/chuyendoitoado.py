import cv2
import numpy as np

def get_projection_matrix():
    """
    Return a homography matrix for camera 1 projection.
    Camera 1 IP: 192.168.66.15
    """
    # Interest points in camera (pixel)
    top_left_point = (184, 181)
    bottom_left_point = (83, 336)
    top_right_point = (395, 174)
    bottom_right_point = (488, 331)

    # Interest points in BIM coordinates (Project coordinates)
    # Hệ tọa độ Revit: E (East) = X, N (North) = Y
    # Camera 1 - dùng BIM coords gốc
    top_left = (70, 27)
    bottom_left = (32, 27)
    top_right = (70, -5)
    bottom_right = (32, -5)

    # Get perspective transformation matrix
    pts1 = np.float32([top_left_point, bottom_left_point, top_right_point, bottom_right_point])
    pts2 = np.float32([top_left, bottom_left, top_right, bottom_right])
    matrix = cv2.getPerspectiveTransform(pts1, pts2)

    return np.array(matrix)
