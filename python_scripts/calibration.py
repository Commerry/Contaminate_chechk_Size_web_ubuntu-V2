import cv2
import numpy as np
import base64
import io

def render_preview(frame, detections):
    """Render preview image (JPEG bytes) with detection boxes and labels."""
    preview_frame = frame.copy()

    for idx, detection in enumerate(detections):
        if 'bbox' in detection:
            x, y, w, h = detection['bbox']
            color = (0, 0, 255)
            cv2.rectangle(preview_frame, (x, y), (x + w, y + h), color, 3)

            width_mm = detection.get('width_mm', 0)
            height_mm = detection.get('height_mm', 0)
            label = f"{width_mm:.1f} x {height_mm:.1f} mm"

            (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(preview_frame, (x, y - label_h - 10), (x + label_w + 8, y), (0, 0, 255), -1)
            cv2.putText(preview_frame, label, (x + 4, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            pixel_label = f"{w}x{h}px"
            cv2.putText(preview_frame, pixel_label, (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    num_detected = len(detections)
    status_text = f"Detected: {num_detected} object(s)"
    status_color = (0, 255, 0) if num_detected >= 2 else (255, 165, 0)

    cv2.rectangle(preview_frame, (5, 5), (280, 45), (0, 0, 0), -1)
    cv2.putText(preview_frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

    if num_detected < 2:
        hint = "Place 50x50mm & 20x20mm objects"
        cv2.putText(preview_frame, hint, (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)

    _, buffer = cv2.imencode('.jpg', preview_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return buffer.tobytes()


def compute_auto_calibration(frame, detections, ref_large_mm=50, ref_small_mm=20):
    """Compute calibration using two reference objects and return result dict.

    Returns dict with keys: calibration_width, calibration_height, calibration_factor,
    formula_width, formula_height, formula_average, accuracy, result_image (base64), detected_objects
    """
    if len(detections) < 2:
        raise ValueError('Need at least 2 detections')

    # sort by area desc
    sorted_detections = sorted(detections, key=lambda d: d.get('bbox', [0,0,0,0])[2] * d.get('bbox', [0,0,0,0])[3], reverse=True)
    large_det = sorted_detections[0]
    small_det = sorted_detections[1]

    large_bbox = large_det['bbox']
    small_bbox = small_det['bbox']

    large_w_px = large_bbox[2]
    large_h_px = large_bbox[3]
    small_w_px = small_bbox[2]
    small_h_px = small_bbox[3]

    pixel_diff_w = large_w_px - small_w_px
    actual_diff_w = ref_large_mm - ref_small_mm
    calibration_width = actual_diff_w / pixel_diff_w if pixel_diff_w > 0 else 0

    pixel_diff_h = large_h_px - small_h_px
    actual_diff_h = ref_large_mm - ref_small_mm
    calibration_height = actual_diff_h / pixel_diff_h if pixel_diff_h > 0 else 0

    calibration_factor = (calibration_width + calibration_height) / 2

    formula_width = f"Width(mm) = Width(px) × {calibration_width:.4f}"
    formula_height = f"Height(mm) = Height(px) × {calibration_height:.4f}"
    formula_avg = f"Size(mm) = Size(px) × {calibration_factor:.4f}"

    large_calculated_w = large_w_px * calibration_width
    large_calculated_h = large_h_px * calibration_height
    small_calculated_w = small_w_px * calibration_width
    small_calculated_h = small_h_px * calibration_height

    large_error_w = abs(large_calculated_w - ref_large_mm) / ref_large_mm * 100
    large_error_h = abs(large_calculated_h - ref_large_mm) / ref_large_mm * 100
    small_error_w = abs(small_calculated_w - ref_small_mm) / ref_small_mm * 100
    small_error_h = abs(small_calculated_h - ref_small_mm) / ref_small_mm * 100

    avg_error = (large_error_w + large_error_h + small_error_w + small_error_h) / 4
    accuracy = max(0, 100 - avg_error)

    # draw result image
    result_frame = frame.copy()

    # large - green
    x, y, w, h = large_bbox
    cv2.rectangle(result_frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
    label_top = f"NEW: {large_calculated_w:.1f}x{large_calculated_h:.1f}mm"
    (label_w, label_h), _ = cv2.getTextSize(label_top, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    cv2.rectangle(result_frame, (x, y - label_h - 10), (x + label_w + 8, y), (0, 255, 0), -1)
    cv2.putText(result_frame, label_top, (x + 4, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    label_bottom = f"Target: {ref_large_mm}x{ref_large_mm}mm ({w}x{h}px)"
    cv2.putText(result_frame, label_bottom, (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # small - blue/orange
    x, y, w, h = small_bbox
    cv2.rectangle(result_frame, (x, y), (x + w, y + h), (255, 200, 0), 3)
    label_top = f"NEW: {small_calculated_w:.1f}x{small_calculated_h:.1f}mm"
    (label_w, label_h), _ = cv2.getTextSize(label_top, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    cv2.rectangle(result_frame, (x, y - label_h - 10), (x + label_w + 8, y), (255, 200, 0), -1)
    cv2.putText(result_frame, label_top, (x + 4, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    label_bottom = f"Target: {ref_small_mm}x{ref_small_mm}mm ({w}x{h}px)"
    cv2.putText(result_frame, label_bottom, (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 2)

    _, buffer = cv2.imencode('.jpg', result_frame)
    result_image_base64 = base64.b64encode(buffer).decode('utf-8')

    data = {
        'calibration_width': round(calibration_width, 4),
        'calibration_height': round(calibration_height, 4),
        'calibration_factor': round(calibration_factor, 4),
        'formula_width': formula_width,
        'formula_height': formula_height,
        'formula_average': formula_avg,
        'accuracy': round(accuracy, 2),
        'result_image': result_image_base64,
        'detected_objects': {
            'large': {
                'width_px': round(large_w_px, 2),
                'height_px': round(large_h_px, 2),
                'width_mm': round(large_calculated_w, 2),
                'height_mm': round(large_calculated_h, 2),
                'reference': f'{ref_large_mm}x{ref_large_mm}mm',
                'bbox': large_bbox
            },
            'small': {
                'width_px': round(small_w_px, 2),
                'height_px': round(small_h_px, 2),
                'width_mm': round(small_calculated_w, 2),
                'height_mm': round(small_calculated_h, 2),
                'reference': f'{ref_small_mm}x{ref_small_mm}mm',
                'bbox': small_bbox
            }
        }
    }

    return data
