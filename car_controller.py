#!/usr/bin/env python3
"""
Car controller module for serial communication with Arduino.
Controls car movement and robotic arm via serial commands.
"""

import serial
import time
from typing import Optional


class CarController:
    """
    Controller for car movement and robotic arm operations.
    Communicates with Arduino Mega 2560 via serial port.
    """
    
    def __init__(self, port: str = '/dev/ttyACM0', baudrate: int = 9600, timeout: float = 1.0):
        """
        Initialize the car controller.
        
        Args:
            port: Serial port path (default: /dev/ttyACM0)
            baudrate: Serial communication baud rate (default: 9600)
            timeout: Serial read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        
        # Default movement duration (seconds)
        self.default_move_duration = 0.5
        self.default_turn_duration = 0.3
        
        # Connect to Arduino
        self.connect()
    
    def connect(self):
        """Establish serial connection to Arduino"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            
            # Wait for Arduino to reset
            time.sleep(2)
            
            # Clear any pending data
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            
            print(f"Connected to Arduino on {self.port} at {self.baudrate} baud")
            
        except serial.SerialException as e:
            print(f"Error connecting to Arduino: {e}")
            raise
    
    def send_command(self, command: str):
        """
        Send a command to Arduino via serial.
        
        Args:
            command: Command string (without newline)
        """
        if not self.serial or not self.serial.is_open:
            print("Warning: Serial port not open")
            return
        
        try:
            # Add newline and encode
            command_with_newline = command + '\n'
            self.serial.write(command_with_newline.encode('utf-8'))
            self.serial.flush()
            
            print(f"Sent command: {command}")
            
        except serial.SerialException as e:
            print(f"Error sending command '{command}': {e}")
    
    def forward(self, duration: Optional[float] = None):
        """
        Move forward.
        
        Args:
            duration: Movement duration in seconds (None = use default)
        """
        if duration is None:
            duration = self.default_move_duration
        
        self.send_command('A')
        time.sleep(duration)
        self.stop()
    
    def backward(self, duration: Optional[float] = None):
        """
        Move backward.
        
        Args:
            duration: Movement duration in seconds (None = use default)
        """
        if duration is None:
            duration = self.default_move_duration
        
        self.send_command('B')
        time.sleep(duration)
        self.stop()
    
    def turn_left(self, duration: Optional[float] = None):
        """
        Turn left.
        
        Args:
            duration: Turn duration in seconds (None = use default)
        """
        if duration is None:
            duration = self.default_turn_duration
        
        self.send_command('L')
        time.sleep(duration)
        self.stop()
    
    def turn_right(self, duration: Optional[float] = None):
        """
        Turn right.
        
        Args:
            duration: Turn duration in seconds (None = use default)
        """
        if duration is None:
            duration = self.default_turn_duration
        
        self.send_command('R')
        time.sleep(duration)
        self.stop()
    
    def rotate_clockwise(self, duration: Optional[float] = None):
        """
        Rotate in place clockwise.
        
        Args:
            duration: Rotation duration in seconds (None = use default)
        """
        if duration is None:
            duration = self.default_turn_duration
        
        self.send_command('rC')
        time.sleep(duration)
        self.stop()
    
    def rotate_counterclockwise(self, duration: Optional[float] = None):
        """
        Rotate in place counter-clockwise.
        
        Args:
            duration: Rotation duration in seconds (None = use default)
        """
        if duration is None:
            duration = self.default_turn_duration
        
        self.send_command('rA')
        time.sleep(duration)
        self.stop()
    
    def stop(self):
        """Stop all movement"""
        self.send_command('S')
        time.sleep(0.1)  # Brief pause to ensure stop command is processed
    
    def set_speed(self, speed: int):
        """
        Set motor speed.
        
        Args:
            speed: Speed value (30, 50, or 80)
        """
        if speed not in [30, 50, 80]:
            print(f"Warning: Speed {speed} not in [30, 50, 80], using anyway")
        
        self.send_command(str(speed))
        time.sleep(0.1)
    
    def grab_block(self):
        """
        Execute block grabbing sequence.
        This sends 'go' command which triggers:
        - approach: arm moves forward
        - clip: gripper closes
        - rise: arm lifts up
        """
        print("Executing grab sequence...")
        self.send_command('go')
        
        # Wait for grab sequence to complete
        # Arduino has delays: 1s + 1s + 1s = 3s, add buffer
        time.sleep(4.0)
        
        print("Grab sequence complete")
    
    def release_block(self):
        """
        Release the grabbed block.
        This sends 'rel' command which opens the gripper.
        """
        print("Releasing block...")
        self.send_command('rel')
        
        # Wait for release to complete
        time.sleep(1.5)
        
        print("Block released")
    
    def align_to_target(self, direction: str, error: int):
        """
        Helper function to align car to a target based on error.
        
        Args:
            direction: 'left', 'right', or 'centered'
            error: Alignment error in pixels
        """
        if direction == 'centered':
            return  # Already aligned
        
        # Calculate turn duration based on error magnitude
        # Larger error = longer turn duration
        turn_time = min(0.1 + abs(error) / 500, 0.5)
        
        if direction == 'left':
            self.turn_left(turn_time)
        elif direction == 'right':
            self.turn_right(turn_time)
    
    def approach_target(self, distance_state: str):
        """
        Helper function to approach a target based on distance estimation.
        
        Args:
            distance_state: 'too_far', 'good', or 'too_close'
        """
        if distance_state == 'good':
            return  # Already at good distance
        
        if distance_state == 'too_far':
            self.forward(0.3)
        elif distance_state == 'too_close':
            self.backward(0.3)
    
    def cleanup(self):
        """Close serial connection"""
        if self.serial and self.serial.is_open:
            self.stop()  # Ensure car is stopped
            time.sleep(0.5)
            self.serial.close()
            print("Serial connection closed")


# Test function
def main():
    """Test the car controller"""
    print("=== Car Controller Test ===")
    print("This will test basic movement commands")
    
    try:
        car = CarController()
        
        print("\nSetting speed to 30...")
        car.set_speed(30)
        time.sleep(1)
        
        print("\nTest 1: Forward")
        car.forward(1.0)
        time.sleep(1)
        
        print("\nTest 2: Backward")
        car.backward(1.0)
        time.sleep(1)
        
        print("\nTest 3: Turn left")
        car.turn_left(0.5)
        time.sleep(1)
        
        print("\nTest 4: Turn right")
        car.turn_right(0.5)
        time.sleep(1)
        
        print("\nTest 5: Rotate clockwise")
        car.rotate_clockwise(0.5)
        time.sleep(1)
        
        print("\nTest 6: Rotate counter-clockwise")
        car.rotate_counterclockwise(0.5)
        time.sleep(1)
        
        print("\nTest complete!")
        
        # Note: Uncomment to test robotic arm
        # print("\nTest 7: Grab block")
        # car.grab_block()
        # time.sleep(2)
        # 
        # print("\nTest 8: Release block")
        # car.release_block()
        
        car.cleanup()
        
    except KeyboardInterrupt:
        print("\nTest interrupted")
        car.cleanup()
    except Exception as e:
        print(f"\nError during test: {e}")


if __name__ == "__main__":
    main()

