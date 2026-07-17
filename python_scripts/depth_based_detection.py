"""
Depth-based Overlapping Object Detection for PSE Vision System
This module enhances the existing measurement system to handle overlapping objects 
using depth information from the OAK camera.
"""

import cv2
import numpy as np
from pathlib import Path
import json

def load_depth_data(depth_path):
    """
    Load depth data from numpy file
    """
    try:
        if depth_path.exists():
            depth = np.load(depth_path)
            return depth
        return None
    except Exception as e:
        print(f"Error loading depth data: {e}")
        return None

def get_depth_at_point(depth_map, x, y):
    """
    Get depth value at specific point (x,y) in depth map
    """
    if depth_map is not None and 0 <= y < depth_map.shape[0] and 0 <= x < depth_map.shape[1]:
        return depth_map[y, x]
    return None

def create_depth_mask(depth_map, min_depth, max_depth):
    """
    Create binary mask based on depth range
    """
    if depth_map is None:
        return None
    
    # Create mask for objects within depth range
    mask = np.zeros_like(depth_map, dtype=np.uint8)
    mask[(depth_map >= min_depth) & (depth_map <= max_depth)] = 255
    return mask

def process_overlapping_objects(image, depth_map, calibration_w, calibration_h):
    """
    Process overlapping objects using depth information to separate them
    
    Args:
        image: Input image (BGR)
        depth_map: Depth map from OAK camera
        calibration_w: Calibration factor for width
        calibration_h: Calibration factor for height
    
    Returns:
        List of measurements with depth-based separation
    """
    
    # Convert image to grayscale for processing
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Thresholding - adjust based on rubber type
    _, binary = cv2.threshold(blurred, 65, 255, cv2.THRESH_BINARY_INV)
    
    # Morphological operations to clean up the mask
    kernel = np.ones((5, 5), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    
    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    measurements = []
    
    # Process each contour to determine if it's overlapping
    for i, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        if area < 50:  # Minimum area threshold
            continue
            
        x, y, w, h = cv2.boundingRect(cnt)
        
        # Get depth information at center of object
        center_x = x + w // 2
        center_y = y + h // 2
        depth_at_center = get_depth_at_point(depth_map, center_x, center_y)
        
        # Calculate real dimensions
        width_mm = w * calibration_w
        height_mm = h * calibration_h
        area_mm2 = width_mm * height_mm
        
        # Determine if object is likely overlapping based on depth
        is_overlapping = False
        if depth_at_center is not None:
            # If we have depth data and object is in a range that suggests overlap
            # This is a heuristic - you might need to tune these values based on your setup
            if depth_at_center > 500:  # Example threshold - adjust as needed
                is_overlapping = True
        
        measurement = {
            'label': f'Object_{i+1}',
            'confidence': 0.9,
            'bbox': [int(x), int(y), int(w), int(h)],
            'width_mm': round(width_mm, 2),
            'height_mm': round(height_mm, 2),
            'area_mm2': round(area_mm2, 2),
            'depth_at_center': depth_at_center,
            'is_overlapping': is_overlapping,
            'timestamp': cv2.getTickCount()
        }
        
        measurements.append(measurement)
    
    return measurements

def separate_overlapping_objects(image, depth_map, measurements):
    """
    Attempt to separate overlapping objects using depth information
    
    Args:
        image: Input image (BGR)
        depth_map: Depth map from OAK camera
        measurements: List of initial measurements
    
    Returns:
        Enhanced measurements with better separation for overlapping objects
    """
    
    if not measurements or len(measurements) < 2:
        return measurements
    
    # Create a depth-based mask to identify object layers
    depth_mask = create_depth_mask(depth_map, 0, 1000)  # Adjust range as needed
    
    # For overlapping objects, we'll try to separate them by depth analysis
    separated_measurements = []
    
    for i, measurement in enumerate(measurements):
        # Check if this object is likely overlapping with others
        if measurement.get('is_overlapping', False):
            # Use depth information to potentially separate
            x, y, w, h = measurement['bbox']
            
            # Create a region of interest around the object
            roi_x1 = max(0, x - 10)
            roi_y1 = max(0, y - 10)
            roi_x2 = min(image.shape[1], x + w + 10)
            roi_y2 = min(image.shape[0], y + h + 10)
            
            # Extract ROI from depth map
            depth_roi = depth_map[roi_y1:roi_y2, roi_x1:roi_x2]
            
            # Analyze depth distribution in this region
            if len(depth_roi[depth_roi > 0]) > 0:
                avg_depth = np.mean(depth_roi[depth_roi > 0])
                std_depth = np.std(depth_roi[depth_roi > 0])
                
                # If there's significant depth variation, it might indicate overlapping objects
                if std_depth > 50:  # Threshold for depth variation - adjust as needed
                    measurement['depth_variation'] = round(std_depth, 2)
                    measurement['estimated_layers'] = max(1, int(std_depth / 100))  # Estimate number of layers
                    
                    # Split the object into multiple measurements based on depth variation
                    # This is a simplified approach - in practice, you'd use more sophisticated methods
                    for layer in range(measurement['estimated_layers']):
                        new_measurement = measurement.copy()
                        new_measurement['layer'] = layer + 1
                        new_measurement['label'] = f"{measurement['label']}_L{layer+1}"
                        # Adjust area calculation for each layer (simplified)
                        new_measurement['area_mm2'] = round(measurement['area_mm2'] / measurement['estimated_layers'], 2)
                        separated_measurements.append(new_measurement)
                else:
                    separated_measurements.append(measurement)
            else:
                separated_measurements.append(measurement)
        else:
            separated_measurements.append(measurement)
    
    return separated_measurements

def enhance_detection_with_depth(image, depth_map, calibration_w, calibration_h):
    """
    Main function to enhance detection using depth information
    
    Args:
        image: Input image (BGR)
        depth_map: Depth map from OAK camera
        calibration_w: Calibration factor for width
        calibration_h: Calibration factor for height
    
    Returns:
        Enhanced measurements with overlapping object handling
    """
    
    # Get initial measurements without depth enhancement
    basic_measurements = process_overlapping_objects(image, depth_map, calibration_w, calibration_h)
    
    # Enhance with depth-based separation
    enhanced_measurements = separate_overlapping_objects(image, depth_map, basic_measurements)
    
    return enhanced_measurements

# Example usage function for testing
def test_depth_detection():
    """
    Test function to demonstrate how the depth detection works
    """
    print("Testing depth-based overlapping object detection...")
    
    # This would be called from the main backend process
    # For now, just showing structure
    
    # Load example image and depth data (this would come from camera_worker)
    # image = cv2.imread('test_image.jpg')
    # depth_map = load_depth_data(Path('runtime/latest_depth.npy'))
    # 
    # measurements = enhance_detection_with_depth(image, depth_map, 1.0, 1.0)
    
    print("Depth-based detection module loaded successfully")

if __name__ == "__main__":
    test_depth_detection()