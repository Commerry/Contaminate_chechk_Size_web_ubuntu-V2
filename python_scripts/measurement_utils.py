"""
Depth-based Object Measurement System
ใช้ RealSense depth camera แยกวัตถุชิ้นบนสุดแล้ววัดขนาด
"""

import cv2
import numpy as np
import pyrealsense2 as rs
from scipy import ndimage

class DepthObjectMeasurer:
    def __init__(self, depth_threshold_mm=50, min_depth_mm=100, max_depth_mm=2000):
        """
        Args:
            depth_threshold_mm: ช่วงความลึกที่ถือว่าเป็นวัตถุเดียวกัน (tolerance)
            min_depth_mm: ระยะใกล้สุดที่รับได้ (กรอง noise)
            max_depth_mm: ระยะไกลสุดที่รับได้
        """
        self.depth_threshold = depth_threshold_mm
        self.min_depth = min_depth_mm
        self.max_depth = max_depth_mm
        self.pipeline = None
        
    def start_camera(self, width=640, height=480, fps=30):
        """เริ่มต้น RealSense camera"""
        self.pipeline = rs.pipeline()
        config = rs.config()
        
        # Enable streams
        config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)
        config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)
        
        # Align depth to color
        align = rs.align(rs.stream.color)
        
        profile = self.pipeline.start(config)
        return align
        
    def stop_camera(self):
        """หยุด camera"""
        if self.pipeline:
            self.pipeline.stop()
            
    def get_top_object_mask(self, depth_frame, method='global'):
        """
        สร้าง mask เฉพาะวัตถุที่อยู่บนสุด (ใกล้กล้องที่สุด)
        
        Args:
            depth_frame: RealSense depth frame
            method: 'global', 'region_growing', 'adaptive'
            
        Returns:
            top_mask: Binary mask ของวัตถุชิ้นบนสุด
            depth_info: ข้อมูล depth เพิ่มเติม
        """
        # แปลง depth frame เป็น numpy array
        depth_image = np.asanyarray(depth_frame.get_data())
        
        # กรองค่าที่ผิดพลาด
        depth_valid = (depth_image > self.min_depth) & (depth_image < self.max_depth)
        depth_image[~depth_valid] = 0
        
        if method == 'global':
            return self._global_threshold(depth_image)
        elif method == 'region_growing':
            return self._region_growing(depth_image)
        elif method == 'adaptive':
            return self._adaptive_threshold(depth_image)
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def _global_threshold(self, depth_image):
        """วิธีที่ 1: ใช้ global threshold - เร็วและง่าย"""
        # หา depth ต่ำสุด (ใกล้กล้องที่สุด)
        valid_depths = depth_image[depth_image > 0]
        if len(valid_depths) == 0:
            return None, {}
            
        min_depth = np.percentile(valid_depths, 1)  # ใช้ percentile เพื่อลด noise
        
        # สร้าง mask: ทุก pixel ที่อยู่ในช่วง min_depth ± threshold
        top_mask = (depth_image > 0) & (depth_image <= min_depth + self.depth_threshold)
        
        # หา connected components
        top_mask_uint8 = top_mask.astype(np.uint8) * 255
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(top_mask_uint8)
        
        if num_labels < 2:
            return None, {}
        
        # เลือก component ที่ใหญ่ที่สุด (ไม่รวม background = label 0)
        areas = stats[1:, cv2.CC_STAT_AREA]  # ข้าม label 0
        largest_label = 1 + np.argmax(areas)
        
        # สร้าง mask สุดท้าย
        final_mask = (labels == largest_label).astype(np.uint8) * 255
        
        # กรอง noise ด้วย morphological operations
        kernel = np.ones((5, 5), np.uint8)
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_OPEN, kernel, iterations=1)
        
        depth_info = {
            'min_depth_mm': min_depth,
            'max_depth_mm': min_depth + self.depth_threshold,
            'method': 'global'
        }
        
        return final_mask, depth_info
    
    def _region_growing(self, depth_image):
        """วิธีที่ 2: Region Growing - แม่นยำกว่า"""
        # หาจุดที่ใกล้กล้องที่สุด (seed point)
        valid_mask = depth_image > 0
        if not np.any(valid_mask):
            return None, {}
            
        # หาจุดที่ depth น้อยที่สุด
        min_indices = np.argmin(np.where(valid_mask, depth_image, np.inf))
        seed_y, seed_x = np.unravel_index(min_indices, depth_image.shape)
        seed_depth = depth_image[seed_y, seed_x]
        
        # Region growing
        from collections import deque
        queue = deque([(seed_y, seed_x)])
        mask = np.zeros_like(depth_image, dtype=bool)
        mask[seed_y, seed_x] = True
        
        # 4-connected neighbors
        neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        
        while queue:
            y, x = queue.popleft()
            current_depth = depth_image[y, x]
            
            for dy, dx in neighbors:
                ny, nx = y + dy, x + dx
                if (0 <= ny < depth_image.shape[0] and 
                    0 <= nx < depth_image.shape[1] and
                    not mask[ny, nx] and
                    depth_image[ny, nx] > 0):
                    
                    # ตรวจสอบว่า depth ใกล้เคียงกันไหม
                    depth_diff = abs(depth_image[ny, nx] - seed_depth)
                    if depth_diff <= self.depth_threshold:
                        mask[ny, nx] = True
                        queue.append((ny, nx))
        
        final_mask = mask.astype(np.uint8) * 255
        
        # Morphological cleanup
        kernel = np.ones((5, 5), np.uint8)
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        depth_info = {
            'seed_depth_mm': seed_depth,
            'seed_position': (seed_x, seed_y),
            'method': 'region_growing'
        }
        
        return final_mask, depth_info
    
    def _adaptive_threshold(self, depth_image):
        """วิธีที่ 3: Adaptive - ปรับ threshold อัตโนมัติตาม distribution"""
        valid_depths = depth_image[depth_image > 0]
        if len(valid_depths) == 0:
            return None, {}
        
        # คำนวณ adaptive threshold จาก distribution
        q1 = np.percentile(valid_depths, 25)
        q3 = np.percentile(valid_depths, 75)
        iqr = q3 - q1
        
        # ใช้ IQR-based threshold
        adaptive_threshold = q1 + 0.5 * iqr
        
        # สร้าง mask
        top_mask = (depth_image > 0) & (depth_image <= adaptive_threshold)
        top_mask_uint8 = top_mask.astype(np.uint8) * 255
        
        # Connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(top_mask_uint8)
        
        if num_labels < 2:
            return None, {}
        
        # เลือก component ที่ใหญ่ที่สุด
        areas = stats[1:, cv2.CC_STAT_AREA]
        largest_label = 1 + np.argmax(areas)
        final_mask = (labels == largest_label).astype(np.uint8) * 255
        
        # Cleanup
        kernel = np.ones((5, 5), np.uint8)
        final_mask = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        depth_info = {
            'adaptive_threshold_mm': adaptive_threshold,
            'q1_mm': q1,
            'q3_mm': q3,
            'method': 'adaptive'
        }
        
        return final_mask, depth_info
    
    def depth_to_color_projection(self, depth_frame, color_frame):
        """แปลง depth coordinates เป็น color coordinates"""
        align = rs.align(rs.stream.color)
        aligned_frames = align.process(rs.composite_frame())
        
        aligned_depth = aligned_frames.get_depth_frame()
        aligned_color = aligned_frames.get_color_frame()
        
        return aligned_depth, aligned_color


# ============================================
# ฟังก์ชันวัดขนาด (ปรับปรุงจากโค้ดเดิม)
# ============================================

def get_contours_with_depth_mask(img, depth_mask, cThr=[100, 100], minArea=1000, filter_points=0):
    """
    หา contours โดยใช้ depth mask เป็นตัวกรอง
    เฉพาะวัตถุที่อยู่ใน depth mask เท่านั้นที่จะถูกวัด
    
    Args:
        img: Color image (BGR)
        depth_mask: Binary mask จาก depth camera
        cThr: Canny thresholds
        minArea: Minimum area
        filter_points: Filter by number of points
        
    Returns:
        contours: List of contours within depth mask
    """
    # แปลงเป็น grayscale
    imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    imgBlur = cv2.GaussianBlur(imgGray, (5, 5), 1)
    
    # Canny edge detection
    imgCanny = cv2.Canny(imgBlur, cThr[0], cThr[1])
    
    # Morphological operations
    kernel = np.ones((5, 5))
    imgDial = cv2.dilate(imgCanny, kernel, iterations=3)
    imgThre = cv2.erode(imgDial, kernel, iterations=2)
    
    # *** สำคัญ: ใช้ depth mask กรอง edges ***
    # เฉพาะ edges ที่อยู่ใน depth mask เท่านั้นที่จะถูกพิจารณา
    imgThre_filtered = cv2.bitwise_and(imgThre, depth_mask)
    
    # Find contours
    contours, _ = cv2.findContours(imgThre_filtered, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # กรอง contours
    final_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > minArea:
            # ตรวจสอบว่า contour นี้อยู่ใน depth mask จริง
            mask = np.zeros(depth_mask.shape, dtype=np.uint8)
            cv2.drawContours(mask, [contour], -1, 255, -1)
            overlap = cv2.bitwise_and(mask, depth_mask)
            overlap_ratio = np.sum(overlap > 0) / np.sum(mask > 0)
            
            # ต้อง overlap อย่างน้อย 50% กับ depth mask
            if overlap_ratio > 0.5:
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
                bbox = cv2.boundingRect(approx)
                
                if filter_points > 0:
                    if len(approx) == filter_points:
                        final_contours.append([len(approx), area, approx, bbox, contour])
                else:
                    final_contours.append([len(approx), area, approx, bbox, contour])
    
    # เรียงตามขนาด
    final_contours = sorted(final_contours, key=lambda x: x[1], reverse=True)
    return final_contours


def measure_top_object_with_depth(frame, depth_frame, reference_width_mm, reference_height_mm,
                                   depth_method='global', min_area=5000, show_debug=False):
    """
    วัดขนาดวัตถุชิ้นบนสุดโดยใช้ depth camera
    
    Args:
        frame: Color frame (BGR)
        depth_frame: RealSense depth frame
        reference_width_mm: ความกว้าง reference ใน mm
        reference_height_mm: ความสูง reference ใน mm
        depth_method: วิธีแยกวัตถุ ('global', 'region_growing', 'adaptive')
        min_area: Minimum contour area
        show_debug: แสดง debug visualization
        
    Returns:
        measurements: List of measurements
        annotated_frame: Frame with annotations
        depth_info: ข้อมูล depth
    """
    measurer = DepthObjectMeasurer(depth_threshold_mm=50)
    
    # 1. สร้าง mask ของวัตถุชิ้นบนสุดจาก depth
    top_mask, depth_info = measurer.get_top_object_mask(depth_frame, method=depth_method)
    
    if top_mask is None:
        print("ไม่พบวัตถุใน depth range ที่กำหนด")
        return [], frame, {}
    
    # 2. หา contours เฉพาะใน top_mask
    contours = get_contours_with_depth_mask(frame, top_mask, minArea=min_area)
    
    if len(contours) == 0:
        print("ไม่พบ contour ที่ตรงกับ depth mask")
        return [], frame, depth_info
    
    # 3. วัดขนาด (ใช้ logic เดิมจากโค้ดของคุณ)
    annotated_frame = frame.copy()
    measurements = []
    
    # แสดง depth mask (debug)
    if show_debug:
        cv2.imshow('Depth Top Mask', top_mask)
    
    for obj in contours:
        num_points, area, approx, bbox, raw_contour = obj
        
        # วาด contour
        cv2.drawContours(annotated_frame, [raw_contour], -1, (0, 255, 0), 2)
        cv2.polylines(annotated_frame, [approx], True, (0, 255, 255), 2)
        
        # คำนวณขนาด (ปรับ scale ตาม distance จาก depth)
        x, y, w, h = bbox
        
        # หา average depth ของวัตถุนั้น
        mask = np.zeros(top_mask.shape, dtype=np.uint8)
        cv2.drawContours(mask, [raw_contour], -1, 255, -1)
        
        depth_image = np.asanyarray(depth_frame.get_data())
        object_depths = depth_image[mask > 0]
        if len(object_depths) > 0:
            avg_depth = np.median(object_depths)
            
            # คำนวณ scale factor ตาม depth
            # ยิ่งไกล ยิ่งเล็ก (ต้อง scale กลับ)
            # สมมติที่ 500mm = 1.0 scale
            scale_factor = 500.0 / avg_depth
            
            # คำนวณขนาดจริง
            width_mm = w * scale_factor * 0.5  # 0.5 = pixel to mm factor (ต้อง calibrate)
            height_mm = h * scale_factor * 0.5
            
            # แสดงผล
            cv2.putText(annotated_frame, 
                       f'W: {width_mm:.1f}mm', 
                       (x, y - 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 
                       0.6, (255, 0, 255), 2)
            cv2.putText(annotated_frame, 
                       f'H: {height_mm:.1f}mm', 
                       (x, y - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 
                       0.6, (255, 0, 255), 2)
            cv2.putText(annotated_frame, 
                       f'Depth: {avg_depth:.0f}mm', 
                       (x, y + h + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 
                       0.6, (0, 255, 255), 2)
            
            measurements.append({
                'width_mm': width_mm,
                'height_mm': height_mm,
                'area_px': area,
                'depth_mm': avg_depth,
                'bbox': bbox
            })
    
    return measurements, annotated_frame, depth_info


# ============================================
# ตัวอย่างการใช้งาน
# ============================================

if __name__ == "__main__":
    # เริ่มต้น camera
    measurer = DepthObjectMeasurer(depth_threshold_mm=30)
    align = measurer.start_camera()
    
    print("กำลังเริ่ม RealSense Camera...")
    print("กด 'q' เพื่อออก, 'd' เพื่อสลับ debug mode")
    
    show_debug = False
    
    try:
        while True:
            # ดึง frames
            frames = measurer.pipeline.wait_for_frames()
            
            # Align depth to color
            aligned_frames = align.process(frames)
            
            color_frame = aligned_frames.get_color_frame()
            depth_frame = aligned_frames.get_depth_frame()
            
            if not color_frame or not depth_frame:
                continue
            
            # แปลงเป็น numpy arrays
            color_image = np.asanyarray(color_frame.get_data())
            
            # วัดขนาดวัตถุชิ้นบนสุด
            measurements, annotated, depth_info = measure_top_object_with_depth(
                color_image,
                depth_frame,
                reference_width_mm=210,  # A4 width
                reference_height_mm=297,  # A4 height
                depth_method='global',  # ลองเปลี่ยนเป็น 'region_growing' หรือ 'adaptive'
                min_area=3000,
                show_debug=show_debug
            )
            
            # แสดงผล
            cv2.imshow('Object Measurement', annotated)
            
            # แสดง depth info
            if depth_info:
                info_text = f"Method: {depth_info.get('method', 'N/A')}"
                cv2.putText(annotated, info_text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Keyboard controls
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('d'):
                show_debug = not show_debug
                print(f"Debug mode: {show_debug}")
    
    finally:
        measurer.stop_camera()
        cv2.destroyAllWindows()
        print("หยุดการทำงาน")




# """
# Utility functions for accurate object measurement
# Based on Real-Time-Object-Measurement by murtazahassan
# https://github.com/murtazahassan/Real-Time-Object-Measurement
# """

# import cv2
# import numpy as np

# def get_contours(img, cThr=[100, 100], showCanny=False, minArea=1000, filter_points=0, draw=False):
#     """
#     Detect contours in image using Canny edge detection
    
#     Args:
#         img: Input image (BGR)
#         cThr: Canny threshold [lower, upper]
#         showCanny: Show Canny edge detection result
#         minArea: Minimum contour area to consider
#         filter_points: Filter contours by number of corner points (0 = no filter, 4 = rectangles)
#         draw: Draw contours on image
        
#     Returns:
#         img: Image with contours drawn (if draw=True)
#         final_contours: List of contours [[num_points, area, approx_points, bbox, raw_contour], ...]
#     """
#     # Convert to grayscale
#     imgGray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
#     # Blur to reduce noise
#     imgBlur = cv2.GaussianBlur(imgGray, (5, 5), 1)
    
#     # Canny edge detection
#     imgCanny = cv2.Canny(imgBlur, cThr[0], cThr[1])
    
#     # Morphological operations to close gaps
#     kernel = np.ones((5, 5))
#     imgDial = cv2.dilate(imgCanny, kernel, iterations=3)
#     imgThre = cv2.erode(imgDial, kernel, iterations=2)
    
#     if showCanny:
#         cv2.imshow('Canny', imgThre)
    
#     # Find contours
#     contours, hierarchy = cv2.findContours(imgThre, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
#     final_contours = []
#     for contour in contours:
#         area = cv2.contourArea(contour)
#         if area > minArea:
#             # Approximate contour to polygon
#             peri = cv2.arcLength(contour, True)
#             approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
#             bbox = cv2.boundingRect(approx)
            
#             # Filter by number of points if specified
#             if filter_points > 0:
#                 if len(approx) == filter_points:
#                     final_contours.append([len(approx), area, approx, bbox, contour])
#             else:
#                 final_contours.append([len(approx), area, approx, bbox, contour])
    
#     # Sort by area (largest first)
#     final_contours = sorted(final_contours, key=lambda x: x[1], reverse=True)
    
#     # Draw contours if requested
#     if draw:
#         for con in final_contours:
#             cv2.drawContours(img, con[4], -1, (0, 0, 255), 3)
    
#     return img, final_contours


# def reorder_points(points):
#     """
#     Reorder 4 corner points to [top-left, top-right, bottom-left, bottom-right]
    
#     Args:
#         points: Array of 4 points [[x,y], [x,y], [x,y], [x,y]]
        
#     Returns:
#         reordered: Points in correct order
#     """
#     points_new = np.zeros_like(points)
#     points = points.reshape((4, 2))
    
#     # Sum of coordinates
#     add = points.sum(1)
#     points_new[0] = points[np.argmin(add)]  # Top-left (smallest sum)
#     points_new[3] = points[np.argmax(add)]  # Bottom-right (largest sum)
    
#     # Difference of coordinates
#     diff = np.diff(points, axis=1)
#     points_new[1] = points[np.argmin(diff)]  # Top-right (smallest diff)
#     points_new[2] = points[np.argmax(diff)]  # Bottom-left (largest diff)
    
#     return points_new


# def warp_image(img, points, w, h, pad=20):
#     """
#     Perform perspective transform to get bird's eye view of object
    
#     Args:
#         img: Input image
#         points: 4 corner points of object
#         w: Output width
#         h: Output height
#         pad: Padding to remove from edges
        
#     Returns:
#         imgWarp: Warped image (bird's eye view)
#     """
#     points = reorder_points(points)
#     pts1 = np.float32(points)
#     pts2 = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
    
#     # Get perspective transform matrix
#     matrix = cv2.getPerspectiveTransform(pts1, pts2)
    
#     # Warp image
#     imgWarp = cv2.warpPerspective(img, matrix, (w, h))
    
#     # Remove padding from edges
#     imgWarp = imgWarp[pad:imgWarp.shape[0]-pad, pad:imgWarp.shape[1]-pad]
    
#     return imgWarp


# def find_distance(pt1, pt2):
#     """
#     Calculate Euclidean distance between two points
    
#     Args:
#         pt1: First point [x, y]
#         pt2: Second point [x, y]
        
#     Returns:
#         distance: Euclidean distance
#     """
#     return ((pt2[0] - pt1[0])**2 + (pt2[1] - pt1[1])**2)**0.5


# def measure_object_with_reference(frame, reference_width_mm, reference_height_mm, 
#                                    min_area=5000, show_visualization=True):
#     """
#     Measure objects using a reference object (like A4 paper)
    
#     Args:
#         frame: Input frame (BGR)
#         reference_width_mm: Known width of reference object in mm (e.g., 210 for A4)
#         reference_height_mm: Known height of reference object in mm (e.g., 297 for A4)
#         min_area: Minimum contour area for reference object
#         show_visualization: Draw measurement annotations
        
#     Returns:
#         measurements: List of measurements [{width_mm, height_mm, bbox}, ...]
#         annotated_frame: Frame with annotations
#     """
#     measurements = []
#     annotated_frame = frame.copy()
    
#     # Scale factor for reference object (e.g., A4 = 210x297mm, scale=3 → 630x891px)
#     scale = 3
#     ref_w_px = int(reference_width_mm * scale)
#     ref_h_px = int(reference_height_mm * scale)
    
#     # Find reference object (largest rectangle, typically)
#     img_contours, contours = get_contours(frame, minArea=min_area, filter_points=4)
    
#     if len(contours) == 0:
#         return measurements, annotated_frame
    
#     # Get largest contour as reference
#     biggest_contour = contours[0][2]  # [num_points, area, approx, bbox, raw]
    
#     # Warp perspective to get flat view
#     img_warp = warp_image(frame, biggest_contour, ref_w_px, ref_h_px)
    
#     # Find objects within the reference area
#     img_contours2, contours2 = get_contours(
#         img_warp, 
#         minArea=2000, 
#         filter_points=4,
#         cThr=[50, 50], 
#         draw=False
#     )
    
#     if len(contours2) == 0:
#         return measurements, annotated_frame
    
#     # Measure each object
#     for obj in contours2:
#         num_points, area, approx, bbox, raw = obj
        
#         # Draw polygon
#         cv2.polylines(annotated_frame, [approx], True, (0, 255, 0), 2)
        
#         # Reorder points to get corners
#         nPoints = reorder_points(approx)
        
#         # Calculate width and height in cm
#         # Distance between corners / scale / 10 = cm
#         width_cm = round((find_distance(nPoints[0][0]//scale, nPoints[1][0]//scale) / 10), 1)
#         height_cm = round((find_distance(nPoints[0][0]//scale, nPoints[2][0]//scale) / 10), 1)
        
#         # Convert to mm
#         width_mm = width_cm * 10
#         height_mm = height_cm * 10
        
#         # Draw measurement arrows
#         cv2.arrowedLine(
#             annotated_frame, 
#             tuple(nPoints[0][0]), 
#             tuple(nPoints[1][0]),
#             (255, 0, 255), 3, 8, 0, 0.05
#         )
#         cv2.arrowedLine(
#             annotated_frame, 
#             tuple(nPoints[0][0]), 
#             tuple(nPoints[2][0]),
#             (255, 0, 255), 3, 8, 0, 0.05
#         )
        
#         # Draw measurements
#         x, y, w, h = bbox
#         cv2.putText(
#             annotated_frame, 
#             f'{width_cm}cm', 
#             (x + 30, y - 10), 
#             cv2.FONT_HERSHEY_COMPLEX_SMALL, 
#             1.5, (255, 0, 255), 2
#         )
#         cv2.putText(
#             annotated_frame, 
#             f'{height_cm}cm', 
#             (x - 70, y + h // 2), 
#             cv2.FONT_HERSHEY_COMPLEX_SMALL, 
#             1.5, (255, 0, 255), 2
#         )
        
#         measurements.append({
#             'width_mm': width_mm,
#             'height_mm': height_mm,
#             'width_cm': width_cm,
#             'height_cm': height_cm,
#             'bbox': bbox
#         })
    
#     return measurements, annotated_frame
