#!/usr/bin/env python3
"""
Main control program for vision-driven block picking and placement robot.
Implements a state machine for autonomous operation.
"""

import cv2
import time
from enum import Enum
from typing import Optional

from vision import VisionSystem, DetectedObject
from car_controller import CarController


class RobotState(Enum):
    """Robot operational states - Simplified version"""
    FIND_BLOCK = 1            # Find colored block nearby
    GRAB_BLOCK = 2            # Execute grab sequence
    ALIGN_TO_TARGET_SHEET = 3 # Align to target colored sheet
    DROP_BLOCK = 4            # Release block
    IDLE = 5                  # Idle state (can restart or stop)


class BlockPickingRobot:
    """
    Main robot controller with state machine for autonomous block picking.
    Integrates vision system and car controller.
    """
    
    def __init__(self, camera_index: int = 0, serial_port: str = '/dev/ttyACM0'):
        """
        Initialize the robot.
        
        Args:
            camera_index: USB camera device index
            serial_port: Arduino serial port path
        """
        print("=== Block Picking Robot Initializing ===")
        
        # Initialize subsystems
        self.vision = VisionSystem(camera_index=camera_index)
        self.car = CarController(port=serial_port)
        
        # Set moderate speed
        self.car.set_speed(50)
        
        # State machine
        self.current_state = RobotState.FIND_BLOCK
        self.previous_state = None
        
        # Task variables
        self.current_block_color = None  # Color of currently grabbed block
        self.blocks_processed = 0
        
        # Timeout and retry parameters
        self.state_timeout = 30.0  # Seconds before giving up on a state
        self.state_start_time = time.time()
        self.search_attempts = 0
        self.max_search_attempts = 20  # Max rotation attempts before giving up
        
        # Alignment parameters
        self.alignment_tolerance = 40  # Pixels (increased for easier alignment)
        self.max_alignment_attempts = 10
        
        # Display window
        self.window_name = "Robot Vision"
        cv2.namedWindow(self.window_name)
        
        print("Robot initialized successfully")
    
    def change_state(self, new_state: RobotState):
        """
        Change robot state.
        
        Args:
            new_state: New state to transition to
        """
        self.previous_state = self.current_state
        self.current_state = new_state
        self.state_start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"STATE: {self.previous_state.name} -> {new_state.name}")
        print(f"{'='*60}")
    
    def check_timeout(self) -> bool:
        """
        Check if current state has timed out.
        
        Returns:
            True if timeout occurred
        """
        elapsed = time.time() - self.state_start_time
        if elapsed > self.state_timeout:
            print(f"WARNING: State {self.current_state.name} timed out after {elapsed:.1f}s")
            return True
        return False
    
    def state_find_block(self, frame) -> bool:
        """
        State: Find a colored block nearby and align to it.
        
        Returns:
            True if block found and aligned
        """
        blocks = self.vision.detect_small_blocks(frame)
        
        if not blocks:
            # No blocks detected, rotate to search
            self.search_attempts += 1
            
            if self.search_attempts > self.max_search_attempts:
                print("WARNING: No blocks found after extensive search!")
                print("Please check if blocks are visible to camera.")
                self.search_attempts = 0
                time.sleep(2)  # Pause before retrying
                return False
            
            print(f"No blocks detected, rotating to search... (attempt {self.search_attempts})")
            self.car.rotate_clockwise(0.3)
            time.sleep(0.3)
            return False
        
        # Reset search attempts
        self.search_attempts = 0
        
        # Found a block, align to it
        block = blocks[0]  # Use largest/closest one
        self.current_block_color = block.color
        
        error, direction = self.vision.calculate_alignment_error(block)
        
        print(f"Block detected: color={block.color}, center=({block.center_x},{block.center_y}), error={error}")
        
        # Align horizontally (don't worry too much about distance for blocks)
        if abs(error) > self.alignment_tolerance:
            print(f"  Aligning: {direction}")
            self.car.align_to_target(direction, error)
            time.sleep(0.2)
            return False
        
        # Aligned to block!
        print(f"✓ Aligned to {block.color.upper()} block, ready to grab")
        return True
    
    def state_grab_block(self) -> bool:
        """
        State: Execute block grabbing sequence.
        
        Returns:
            True when grab complete
        """
        print(f"\n{'='*50}")
        print(f"🤖 GRABBING {self.current_block_color.upper()} BLOCK...")
        print(f"{'='*50}")
        
        self.car.grab_block()
        
        print(f"✓ Grab complete!")
        print(f"  Total blocks processed: {self.blocks_processed + 1}")
        self.blocks_processed += 1
        return True
    
    def state_align_to_target_sheet(self, frame) -> bool:
        """
        State: Find and align to target colored sheet using vision.
        
        Returns:
            True when aligned and ready to drop
        """
        # Detect sheet of target color
        sheets = self.vision.detect_sheets(frame, colors=[self.current_block_color])
        
        if not sheets:
            # Target sheet not visible, rotate to search
            self.search_attempts += 1
            
            if self.search_attempts > self.max_search_attempts:
                print(f"WARNING: Cannot find {self.current_block_color.upper()} sheet after extensive search!")
                print("Please check if the target sheet is visible.")
                self.search_attempts = 0
                time.sleep(2)
                return False
            
            print(f"No {self.current_block_color.upper()} sheet detected, rotating... (attempt {self.search_attempts})")
            self.car.rotate_clockwise(0.3)
            time.sleep(0.3)
            return False
        
        # Reset search attempts
        self.search_attempts = 0
        
        # Found target sheet, align to it
        target_sheet = sheets[0]
        
        error, direction = self.vision.calculate_alignment_error(target_sheet)
        distance = self.vision.estimate_distance(target_sheet, reference_area=20000)
        
        print(f"{self.current_block_color.upper()} sheet found: error={error}, distance={distance}")
        
        # Align horizontally first
        if abs(error) > self.alignment_tolerance:
            print(f"  Aligning: {direction}")
            self.car.align_to_target(direction, error)
            time.sleep(0.2)
            return False
        
        # Then adjust distance
        if distance == 'too_far':
            print(f"  Moving closer...")
            self.car.forward(0.4)
            time.sleep(0.2)
            return False
        elif distance == 'too_close':
            print(f"  Moving back...")
            self.car.backward(0.3)
            time.sleep(0.2)
            return False
        
        # Aligned!
        print(f"✓ Successfully aligned to {self.current_block_color.upper()} target sheet")
        return True
    
    def state_drop_block(self) -> bool:
        """
        State: Release the block.
        
        Returns:
            True when drop complete
        """
        print(f"\n{'='*50}")
        print(f"📦 DROPPING {self.current_block_color.upper()} BLOCK...")
        print(f"{'='*50}")
        
        self.car.release_block()
        
        print(f"✓ Block dropped successfully at {self.current_block_color.upper()} zone")
        self.current_block_color = None
        return True
    
    def state_idle(self) -> bool:
        """
        State: Idle state after completing a task.
        User can manually reposition the car or press 'c' to continue.
        
        Returns:
            False (stays in idle until user action)
        """
        print("\n" + "="*60)
        print("🎉 TASK COMPLETED!")
        print(f"   Total blocks processed: {self.blocks_processed}")
        print("="*60)
        print("\nOptions:")
        print("  - Press 'C' to continue with next block")
        print("  - Press 'Q' to quit")
        print("  - Or manually reposition the car and press 'C'")
        print("\nWaiting for command...")
        
        # This state will stay here until user presses 'C' or 'Q'
        return False
    
    def run_state_machine(self, frame):
        """
        Execute one iteration of the state machine.
        
        Args:
            frame: Current camera frame
        """
        # Skip timeout check for IDLE state
        if self.current_state != RobotState.IDLE:
            # Check for timeout
            if self.check_timeout():
                print("State timed out, returning to FIND_BLOCK")
                self.change_state(RobotState.FIND_BLOCK)
                return
        
        # Execute current state
        state_complete = False
        
        if self.current_state == RobotState.FIND_BLOCK:
            state_complete = self.state_find_block(frame)
            if state_complete:
                self.change_state(RobotState.GRAB_BLOCK)
        
        elif self.current_state == RobotState.GRAB_BLOCK:
            state_complete = self.state_grab_block()
            if state_complete:
                self.change_state(RobotState.ALIGN_TO_TARGET_SHEET)
        
        elif self.current_state == RobotState.ALIGN_TO_TARGET_SHEET:
            state_complete = self.state_align_to_target_sheet(frame)
            if state_complete:
                self.change_state(RobotState.DROP_BLOCK)
        
        elif self.current_state == RobotState.DROP_BLOCK:
            state_complete = self.state_drop_block()
            if state_complete:
                self.change_state(RobotState.IDLE)
        
        elif self.current_state == RobotState.IDLE:
            state_complete = self.state_idle()
            # Will stay in IDLE until user presses 'C' to continue
    
    def run(self):
        """Main robot control loop"""
        print("\n" + "="*60)
        print("🤖 SIMPLIFIED BLOCK PICKING ROBOT")
        print("="*60)
        print("\nWorkflow:")
        print("  1. Find nearby block (RED/YELLOW/BLUE)")
        print("  2. Grab the block")
        print("  3. Find matching colored sheet")
        print("  4. Drop the block")
        print("  5. Wait for next command")
        print("\nControls:")
        print("  Q - Quit program")
        print("  C - Continue to next block (when in IDLE)")
        print("  R - Reset to FIND_BLOCK state")
        print("="*60)
        
        input("\nPress ENTER to start...")
        
        try:
            while True:
                # Capture frame
                frame = self.vision.capture_frame()
                if frame is None:
                    print("Warning: Failed to capture frame")
                    time.sleep(0.1)
                    continue
                
                # Detect objects for visualization
                blocks = self.vision.detect_small_blocks(frame)
                sheets = self.vision.detect_sheets(frame)
                
                # Draw detections
                annotated_frame = self.vision.draw_detections(frame, blocks, sheets)
                
                # Add state information overlay
                state_text = f"STATE: {self.current_state.name}"
                cv2.putText(annotated_frame, state_text, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                if self.current_block_color:
                    color_text = f"CURRENT: {self.current_block_color.upper()}"
                    cv2.putText(annotated_frame, color_text, (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                processed_text = f"COMPLETED: {self.blocks_processed}"
                cv2.putText(annotated_frame, processed_text, (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Run state machine
                self.run_state_machine(frame)
                
                # Display frame
                cv2.imshow(self.window_name, annotated_frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    print("\n\n🛑 Quitting...")
                    break
                elif key == ord('c'):
                    if self.current_state == RobotState.IDLE:
                        print("\n\n▶️  Continuing to next block...")
                        self.change_state(RobotState.FIND_BLOCK)
                    else:
                        print("\n⚠️  Can only continue from IDLE state")
                elif key == ord('r'):
                    print("\n\n🔄 Resetting to FIND_BLOCK state...")
                    self.current_block_color = None
                    self.change_state(RobotState.FIND_BLOCK)
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.05)
        
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        print("\nCleaning up...")
        self.car.stop()
        self.car.cleanup()
        self.vision.cleanup()
        cv2.destroyAllWindows()
        print("Cleanup complete")


def main():
    """Entry point"""
    print("="*60)
    print("Block Picking Robot - Main Program")
    print("="*60)
    
    # Parse command line arguments (optional)
    import sys
    
    camera_index = 0
    serial_port = '/dev/ttyACM0'
    
    if len(sys.argv) > 1:
        camera_index = int(sys.argv[1])
    
    if len(sys.argv) > 2:
        serial_port = sys.argv[2]
    
    print(f"Camera index: {camera_index}")
    print(f"Serial port: {serial_port}")
    print()
    
    try:
        robot = BlockPickingRobot(camera_index=camera_index, serial_port=serial_port)
        robot.run()
    
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

