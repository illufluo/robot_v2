#!/usr/bin/env python3
"""
Vision module for block detection and A4 sheet detection.
Uses USB camera with OpenCV for color-based object detection.
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class DetectedObject:
    """Data class for detected objects (blocks or sheets)"""
    color: str
    center_x: int
    center_y: int
    area: float
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    aspect_ratio: float


class VisionSystem:
    """
    Vision system for detecting small colored blocks and vertical A4 sheets.
    Supports Red, Yellow, Blue colored objects and Black sheets (start point).
    """
    
    def __init__(self, camera_index=0, resolution=(640, 480)):
        """
        Initialize the vision system.
        
        Args:
            camera_index: USB camera device index (usually 0)
            resolution: Camera resolution tuple (width, height)
        """
        self.camera_index = camera_index
        self.resolution = resolution
        self.camera = None
        
        # HSV color ranges for detection
        # Format: {color_name: [(lower_hsv, upper_hsv), ...]}
        self.color_ranges = {
            'red': [
                # Red wraps around in HSV space
                (np.array([0, 100, 100]), np.array([10, 255, 255])),
                (np.array([160, 100, 100]), np.array([180, 255, 255]))
            ],
            'yellow': [
                (np.array([20, 100, 100]), np.array([35, 255, 255]))
            ],
            'blue': [
                (np.array([100, 100, 80]), np.array([130, 255, 255]))
            ],
            'black': [
                # Black has low V (value/brightness)
                (np.array([0, 0, 0]), np.array([180, 255, 50]))
            ]
        }
        
        # Detection parameters
        self.block_min_area = 300       # Minimum area for small blocks
        self.block_max_area = 5000      # Maximum area for small blocks
        self.sheet_min_area = 8000      # Minimum area for A4 sheets
        self.sheet_max_area = 100000    # Maximum area for A4 sheets
        
        # Aspect ratio thresholds
        self.block_aspect_ratio_range = (0.5, 2.0)   # Blocks are roughly square
        self.sheet_aspect_ratio_range = (0.3, 0.9)   # Vertical A4: height > width
        
        # Morphological kernel for noise reduction
        self.kernel = np.ones((5, 5), np.uint8)
        
        # Camera frame center
        self.frame_center_x = resolution[0] // 2
        self.frame_center_y = resolution[1] // 2
        
        # Initialize camera
        self.setup_camera()
    
    def setup_camera(self):
        """Initialize USB camera"""
        self.camera = cv2.VideoCapture(self.camera_index)
        
        if not self.camera.isOpened():
            raise RuntimeError(f"Failed to open camera {self.camera_index}")
        
        # Set resolution
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        
        # Warm up camera
        for _ in range(5):
            self.camera.read()
        
        print(f"Camera initialized at {self.resolution[0]}x{self.resolution[1]}")
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """
        Capture a single frame from camera.
        
        Returns:
            Frame in BGR format, or None if capture fails
        """
        ret, frame = self.camera.read()
        if not ret:
            print("Warning: Failed to capture frame")
            return None
        return frame
    
    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess frame for color detection.
        
        Args:
            frame: Input frame in BGR format
            
        Returns:
            Frame in HSV color space
        """
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(frame, (5, 5), 0)
        
        # Convert to HSV
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        
        return hsv
    
    def create_color_mask(self, hsv_frame: np.ndarray, color: str) -> np.ndarray:
        """
        Create binary mask for a specific color.
        
        Args:
            hsv_frame: Frame in HSV color space
            color: Color name ('red', 'yellow', 'blue', 'black')
            
        Returns:
            Binary mask
        """
        if color not in self.color_ranges:
            raise ValueError(f"Color '{color}' not supported")
        
        mask = np.zeros(hsv_frame.shape[:2], dtype=np.uint8)
        
        # Apply each HSV range for the color
        for lower, upper in self.color_ranges[color]:
            mask = cv2.bitwise_or(mask, cv2.inRange(hsv_frame, lower, upper))
        
        # Morphological operations to reduce noise
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel)
        
        return mask
    
    def extract_objects_from_mask(self, mask: np.ndarray, color: str,
                                   min_area: float, max_area: float,
                                   aspect_ratio_range: Tuple[float, float]) -> List[DetectedObject]:
        """
        Extract objects from a color mask based on area and aspect ratio constraints.
        
        Args:
            mask: Binary mask
            color: Color name
            min_area: Minimum contour area
            max_area: Maximum contour area
            aspect_ratio_range: (min_ratio, max_ratio) for width/height
            
        Returns:
            List of DetectedObject
        """
        objects = []
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Filter by area
            if area < min_area or area > max_area:
                continue
            
            # Get bounding box
            x, y, w, h = cv2.boundingRect(contour)
            
            # Calculate aspect ratio (width / height)
            aspect_ratio = w / h if h > 0 else 0
            
            # Filter by aspect ratio
            if aspect_ratio < aspect_ratio_range[0] or aspect_ratio > aspect_ratio_range[1]:
                continue
            
            # Calculate center
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
            else:
                cx = x + w // 2
                cy = y + h // 2
            
            obj = DetectedObject(
                color=color,
                center_x=cx,
                center_y=cy,
                area=area,
                bbox=(x, y, w, h),
                aspect_ratio=aspect_ratio
            )
            
            objects.append(obj)
        
        # Sort by area (largest first)
        objects.sort(key=lambda o: o.area, reverse=True)
        
        return objects
    
    def detect_small_blocks(self, frame: np.ndarray, 
                           colors: List[str] = ['red', 'yellow', 'blue']) -> List[DetectedObject]:
        """
        Detect small colored blocks on the ground.
        Blocks are characterized by: medium area, roughly square aspect ratio.
        
        Args:
            frame: Input frame in BGR format
            colors: List of colors to detect
            
        Returns:
            List of detected blocks
        """
        hsv_frame = self.preprocess_frame(frame)
        all_blocks = []
        
        for color in colors:
            mask = self.create_color_mask(hsv_frame, color)
            blocks = self.extract_objects_from_mask(
                mask, color,
                self.block_min_area,
                self.block_max_area,
                self.block_aspect_ratio_range
            )
            all_blocks.extend(blocks)
        
        # Sort by area (largest first)
        all_blocks.sort(key=lambda b: b.area, reverse=True)
        
        return all_blocks
    
    def detect_sheets(self, frame: np.ndarray,
                     colors: List[str] = ['black', 'red', 'yellow', 'blue']) -> List[DetectedObject]:
        """
        Detect vertical A4 sheets (large colored papers).
        Sheets are characterized by: large area, vertical rectangle (height > width).
        
        Args:
            frame: Input frame in BGR format
            colors: List of colors to detect
            
        Returns:
            List of detected sheets
        """
        hsv_frame = self.preprocess_frame(frame)
        all_sheets = []
        
        for color in colors:
            mask = self.create_color_mask(hsv_frame, color)
            sheets = self.extract_objects_from_mask(
                mask, color,
                self.sheet_min_area,
                self.sheet_max_area,
                self.sheet_aspect_ratio_range
            )
            all_sheets.extend(sheets)
        
        # Sort by area (largest first)
        all_sheets.sort(key=lambda s: s.area, reverse=True)
        
        return all_sheets
    
    def calculate_alignment_error(self, obj: DetectedObject) -> Tuple[int, str]:
        """
        Calculate horizontal alignment error for an object.
        
        Args:
            obj: Detected object
            
        Returns:
            Tuple of (error_in_pixels, direction)
            direction is 'left', 'right', or 'centered'
        """
        error = obj.center_x - self.frame_center_x
        
        # Threshold for considering centered
        center_threshold = 30
        
        if abs(error) < center_threshold:
            return error, 'centered'
        elif error > 0:
            return error, 'right'  # Object is to the right, need to turn right
        else:
            return error, 'left'   # Object is to the left, need to turn left
    
    def estimate_distance(self, obj: DetectedObject, reference_area: float = 20000) -> str:
        """
        Estimate relative distance to object based on its area.
        
        Args:
            obj: Detected object
            reference_area: Reference area for "good" distance
            
        Returns:
            'too_close', 'good', or 'too_far'
        """
        area_ratio = obj.area / reference_area
        
        if area_ratio > 1.5:
            return 'too_close'
        elif area_ratio < 0.5:
            return 'too_far'
        else:
            return 'good'
    
    def draw_detections(self, frame: np.ndarray,
                       blocks: List[DetectedObject],
                       sheets: List[DetectedObject]) -> np.ndarray:
        """
        Draw detection results on frame for visualization.
        
        Args:
            frame: Input frame
            blocks: Detected blocks
            sheets: Detected sheets
            
        Returns:
            Annotated frame
        """
        annotated = frame.copy()
        
        # Color map for drawing (BGR format)
        color_map = {
            'red': (0, 0, 255),
            'yellow': (0, 255, 255),
            'blue': (255, 0, 0),
            'black': (128, 128, 128)
        }
        
        # Draw blocks with solid rectangles
        for block in blocks:
            color = color_map.get(block.color, (255, 255, 255))
            x, y, w, h = block.bbox
            
            # Draw bounding box
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 2)
            
            # Draw center
            cv2.circle(annotated, (block.center_x, block.center_y), 5, color, -1)
            
            # Label
            label = f"BLOCK:{block.color} A:{int(block.area)}"
            cv2.putText(annotated, label, (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Draw sheets with dashed-style rectangles
        for sheet in sheets:
            color = color_map.get(sheet.color, (255, 255, 255))
            x, y, w, h = sheet.bbox
            
            # Draw bounding box (thicker)
            cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 3)
            
            # Draw center
            cv2.circle(annotated, (sheet.center_x, sheet.center_y), 8, color, -1)
            
            # Label
            label = f"SHEET:{sheet.color} A:{int(sheet.area)}"
            cv2.putText(annotated, label, (x, y - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Draw frame center cross
        cv2.line(annotated,
                (self.frame_center_x - 20, self.frame_center_y),
                (self.frame_center_x + 20, self.frame_center_y),
                (0, 255, 0), 2)
        cv2.line(annotated,
                (self.frame_center_x, self.frame_center_y - 20),
                (self.frame_center_x, self.frame_center_y + 20),
                (0, 255, 0), 2)
        
        return annotated
    
    def cleanup(self):
        """Release camera resources"""
        if self.camera:
            self.camera.release()
            print("Camera released")


# Test function
def main():
    """Test the vision system"""
    print("=== Vision System Test ===")
    
    vision = VisionSystem(camera_index=0)
    
    print("Press 'q' to quit, 'b' to toggle block detection, 's' to toggle sheet detection")
    
    show_blocks = True
    show_sheets = True
    
    try:
        while True:
            frame = vision.capture_frame()
            if frame is None:
                continue
            
            blocks = []
            sheets = []
            
            if show_blocks:
                blocks = vision.detect_small_blocks(frame)
            
            if show_sheets:
                sheets = vision.detect_sheets(frame)
            
            # Draw detections
            annotated = vision.draw_detections(frame, blocks, sheets)
            
            # Add info text
            info_y = 30
            cv2.putText(annotated, f"Blocks: {len(blocks)}", (10, info_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            info_y += 25
            cv2.putText(annotated, f"Sheets: {len(sheets)}", (10, info_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Print detection info
            if blocks:
                print(f"Blocks: ", end="")
                for b in blocks[:3]:  # Show first 3
                    print(f"{b.color}({b.center_x},{b.center_y}) ", end="")
                print()
            
            if sheets:
                print(f"Sheets: ", end="")
                for s in sheets[:3]:
                    print(f"{s.color}({s.center_x},{s.center_y}) ", end="")
                print()
            
            cv2.imshow('Vision System Test', annotated)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('b'):
                show_blocks = not show_blocks
                print(f"Block detection: {'ON' if show_blocks else 'OFF'}")
            elif key == ord('s'):
                show_sheets = not show_sheets
                print(f"Sheet detection: {'ON' if show_sheets else 'OFF'}")
    
    except KeyboardInterrupt:
        print("\nInterrupted")
    
    finally:
        vision.cleanup()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

