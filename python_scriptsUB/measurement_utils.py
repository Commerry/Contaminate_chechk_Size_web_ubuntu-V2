"""
Utility functions for accurate object measurement
Based on Real-Time-Object-Measurement by murtazahassan
https://github.com/murtazahassan/Real-Time-Object-Measurement
"""

import cv2
import numpy as np

def get_contours(img, cThr=[100, 100], showCanny=False, minArea=1000, filter_points=0, draw=False):
    """
    Detect contours in image using Canny edge detection
    
    Args:
        img: Input image (BGR)
        cThr: Canny threshold [lower, upper]
        showCanny: Show Canny edge detection result
        minArea: Minimum contour area to consider
        filter_points: Filter contours by number of corner points (0 = no filter, 4 = rectangles)
        draw: Draw contours on image
        
    Returns:
        img: Image with contours drawn (if draw=True)
        final_contours: List of contours [[num_points, area, approx_points, bbox, raw_contour], ...]
    """
    # Convert to grayscale
    imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Blur to reduce noise
    imgBlur = cv2.GaussianBlur(imgGray, (5, 5), 1)
    
    # Canny edge detection
    imgCanny = cv2.Canny(imgBlur, cThr[0], cThr[1])
    
    # Morphological operations to close gaps
    kernel = np.ones((5, 5))
    imgDial = cv2.dilate(imgCanny, kernel, iterations=3)
    imgThre = cv2.erode(imgDial, kernel, iterations=2)
    
    if showCanny:
        cv2.imshow('Canny', imgThre)
    
    # Find contours
    contours, hierarchy = cv2.findContours(imgThre, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    final_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > minArea:
            # Approximate contour to polygon
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            bbox = cv2.boundingRect(approx)
            
            # Filter by number of points if specified
            if filter_points > 0:
                if len(approx) == filter_points:
                    final_contours.append([len(approx), area, approx, bbox, contour])
            else:
                final_contours.append([len(approx), area, approx, bbox, contour])
    
    # Sort by area (largest first)
    final_contours = sorted(final_contours, key=lambda x: x[1], reverse=True)
    
    # Draw contours if requested
    if draw:
        for con in final_contours:
            cv2.drawContours(img, con[4], -1, (0, 0, 255), 3)
    
    return img, final_contours


def reorder_points(points):
    """
    Reorder 4 corner points to [top-left, top-right, bottom-left, bottom-right]
    
    Args:
        points: Array of 4 points [[x,y], [x,y], [x,y], [x,y]]
        
    Returns:
        reordered: Points in correct order
    """
    points_new = np.zeros_like(points)
    points = points.reshape((4, 2))
    
    # Sum of coordinates
    add = points.sum(1)
    points_new[0] = points[np.argmin(add)]  # Top-left (smallest sum)
    points_new[3] = points[np.argmax(add)]  # Bottom-right (largest sum)
    
    # Difference of coordinates
    diff = np.diff(points, axis=1)
    points_new[1] = points[np.argmin(diff)]  # Top-right (smallest diff)
    points_new[2] = points[np.argmax(diff)]  # Bottom-left (largest diff)
    
    return points_new


def warp_image(img, points, w, h, pad=20):
    """
    Perform perspective transform to get bird's eye view of object
    
    Args:
        img: Input image
        points: 4 corner points of object
        w: Output width
        h: Output height
        pad: Padding to remove from edges
        
    Returns:
        imgWarp: Warped image (bird's eye view)
    """
    points = reorder_points(points)
    pts1 = np.float32(points)
    pts2 = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
    
    # Get perspective transform matrix
    matrix = cv2.getPerspectiveTransform(pts1, pts2)
    
    # Warp image
    imgWarp = cv2.warpPerspective(img, matrix, (w, h))
    
    # Remove padding from edges
    imgWarp = imgWarp[pad:imgWarp.shape[0]-pad, pad:imgWarp.shape[1]-pad]
    
    return imgWarp


def find_distance(pt1, pt2):
    """
    Calculate Euclidean distance between two points
    
    Args:
        pt1: First point [x, y]
        pt2: Second point [x, y]
        
    Returns:
        distance: Euclidean distance
    """
    return ((pt2[0] - pt1[0])**2 + (pt2[1] - pt1[1])**2)**0.5


def measure_object_with_reference(frame, reference_width_mm, reference_height_mm, 
                                   min_area=5000, show_visualization=True):
    """
    Measure objects using a reference object (like A4 paper)
    
    Args:
        frame: Input frame (BGR)
        reference_width_mm: Known width of reference object in mm (e.g., 210 for A4)
        reference_height_mm: Known height of reference object in mm (e.g., 297 for A4)
        min_area: Minimum contour area for reference object
        show_visualization: Draw measurement annotations
        
    Returns:
        measurements: List of measurements [{width_mm, height_mm, bbox}, ...]
        annotated_frame: Frame with annotations
    """
    measurements = []
    annotated_frame = frame.copy()
    
    # Scale factor for reference object (e.g., A4 = 210x297mm, scale=3 → 630x891px)
    scale = 3
    ref_w_px = int(reference_width_mm * scale)
    ref_h_px = int(reference_height_mm * scale)
    
    # Find reference object (largest rectangle, typically)
    img_contours, contours = get_contours(frame, minArea=min_area, filter_points=4)
    
    if len(contours) == 0:
        return measurements, annotated_frame
    
    # Get largest contour as reference
    biggest_contour = contours[0][2]  # [num_points, area, approx, bbox, raw]
    
    # Warp perspective to get flat view
    img_warp = warp_image(frame, biggest_contour, ref_w_px, ref_h_px)
    
    # Find objects within the reference area
    img_contours2, contours2 = get_contours(
        img_warp, 
        minArea=2000, 
        filter_points=4,
        cThr=[50, 50], 
        draw=False
    )
    
    if len(contours2) == 0:
        return measurements, annotated_frame
    
    # Measure each object
    for obj in contours2:
        num_points, area, approx, bbox, raw = obj
        
        # Draw polygon
        cv2.polylines(annotated_frame, [approx], True, (0, 255, 0), 2)
        
        # Reorder points to get corners
        nPoints = reorder_points(approx)
        
        # Calculate width and height in cm
        # Distance between corners / scale / 10 = cm
        width_cm = round((find_distance(nPoints[0][0]//scale, nPoints[1][0]//scale) / 10), 1)
        height_cm = round((find_distance(nPoints[0][0]//scale, nPoints[2][0]//scale) / 10), 1)
        
        # Convert to mm
        width_mm = width_cm * 10
        height_mm = height_cm * 10
        
        # Draw measurement arrows
        cv2.arrowedLine(
            annotated_frame, 
            tuple(nPoints[0][0]), 
            tuple(nPoints[1][0]),
            (255, 0, 255), 3, 8, 0, 0.05
        )
        cv2.arrowedLine(
            annotated_frame, 
            tuple(nPoints[0][0]), 
            tuple(nPoints[2][0]),
            (255, 0, 255), 3, 8, 0, 0.05
        )
        
        # Draw measurements
        x, y, w, h = bbox
        cv2.putText(
            annotated_frame, 
            f'{width_cm}cm', 
            (x + 30, y - 10), 
            cv2.FONT_HERSHEY_COMPLEX_SMALL, 
            1.5, (255, 0, 255), 2
        )
        cv2.putText(
            annotated_frame, 
            f'{height_cm}cm', 
            (x - 70, y + h // 2), 
            cv2.FONT_HERSHEY_COMPLEX_SMALL, 
            1.5, (255, 0, 255), 2
        )
        
        measurements.append({
            'width_mm': width_mm,
            'height_mm': height_mm,
            'width_cm': width_cm,
            'height_cm': height_cm,
            'bbox': bbox
        })
    
    return measurements, annotated_frame
