import cv2
import numpy as np

# อ่านภาพ
image = cv2.imread('Image.jpg')  # แทนที่ด้วยชื่อไฟล์ภาพของคุณ
if image is None:
    raise ValueError("ไม่สามารถโหลดภาพได้")

# เปลี่ยนภาพจาก BGR เป็น HSV
hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

# กำหนดช่วงสี (ตัวอย่าง: สีแดง)
lower_red = np.array([0, 50, 50])
upper_red = np.array([10, 255, 255])

# สร้าง mask สำหรับสีแดง
mask_red = cv2.inRange(hsv, lower_red, upper_red)

# หา contours จาก mask
contours, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# วาด contours บนภาพต้นฉบับ
result_image = image.copy()
cv2.drawContours(result_image, contours, -1, (0, 255, 0), 2)  # สีเขียวสำหรับ contours

# แสดงผล
cv2.imshow('Original Image', image)
cv2.imshow('Mask Red', mask_red)
cv2.imshow('Contours', result_image)

cv2.waitKey(0)
cv2.destroyAllWindows()