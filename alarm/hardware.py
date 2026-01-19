"""Hardware controls for alarm: button and volume potentiometer."""

import subprocess
import threading
import time
from typing import Callable, Optional

# Hardware available flag
HARDWARE_AVAILABLE = False

try:
    from gpiozero import Button
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    HARDWARE_AVAILABLE = True
except ImportError as e:
    print(f"[Hardware] Libraries not available: {e}")
except Exception as e:
    print(f"[Hardware] Error loading libraries: {e}")


class HardwareController:
    """Controls physical button and volume potentiometer."""
    
    # GPIO pin for stop button
    BUTTON_GPIO = 17
    
    # Volume update threshold (percent) - only update if change exceeds this
    VOLUME_THRESHOLD = 3
    
    # Polling interval for potentiometer (seconds)
    POLL_INTERVAL = 0.1
    
    def __init__(self, on_button_press: Callable[[], None]):
        """
        Initialize hardware controller.
        
        Args:
            on_button_press: Callback function when button is pressed
        """
        self._on_button_press = on_button_press
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_volume = -1  # Track last set volume to avoid redundant calls
        
        self._button: Optional[Button] = None
        self._pot: Optional[AnalogIn] = None
        
        if not HARDWARE_AVAILABLE:
            print("[Hardware] Hardware libraries not available, running in software-only mode")
            return
        
        try:
            # Initialize button on GPIO 17 with internal pull-up
            # Button connects GPIO to GND when pressed
            self._button = Button(
                self.BUTTON_GPIO, 
                pull_up=True, 
                bounce_time=0.2  # 200ms debounce
            )
            self._button.when_pressed = self._handle_button_press
            print(f"[Hardware] Button initialized on GPIO {self.BUTTON_GPIO}")
            
            # Initialize ADS1115 ADC on I2C
            i2c = busio.I2C(board.SCL, board.SDA)
            ads = ADS.ADS1115(i2c)
            # Set gain for 0-4.096V range (works well with 3.3V logic)
            ads.gain = 1
            self._pot = AnalogIn(ads, ADS.P0)  # Channel A0
            print("[Hardware] ADS1115 ADC initialized on I2C (channel A0)")
            
        except Exception as e:
            print(f"[Hardware] Error initializing hardware: {e}")
            self._button = None
            self._pot = None
    
    def _handle_button_press(self):
        """Handle button press event."""
        print("[Hardware] Stop button pressed")
        if self._on_button_press:
            self._on_button_press()
    
    def read_volume_percent(self) -> int:
        """
        Read potentiometer and return volume percentage (0-100).
        
        Returns:
            Volume percentage, or -1 if hardware unavailable
        """
        if self._pot is None:
            return -1
        
        try:
            # ADS1115 returns 16-bit signed value (0 to 32767 for positive voltages)
            # Map to 0-100 percent
            raw_value = self._pot.value
            # Clamp to valid range and convert
            percent = max(0, min(100, int(raw_value / 327.67)))
            return percent
        except Exception as e:
            print(f"[Hardware] Error reading potentiometer: {e}")
            return -1
    
    def set_system_volume(self, percent: int) -> bool:
        """
        Set system volume using amixer.
        
        Args:
            percent: Volume level 0-100
            
        Returns:
            True if successful
        """
        percent = max(0, min(100, percent))
        
        try:
            result = subprocess.run(
                ["amixer", "set", "Master", f"{percent}%"],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print("[Hardware] amixer timed out")
            return False
        except FileNotFoundError:
            # Try with card specification
            try:
                result = subprocess.run(
                    ["amixer", "-c", "0", "set", "Master", f"{percent}%"],
                    capture_output=True,
                    timeout=2
                )
                return result.returncode == 0
            except Exception:
                return False
        except Exception as e:
            print(f"[Hardware] Error setting volume: {e}")
            return False
    
    def _poll_loop(self):
        """Background thread that polls the potentiometer."""
        print("[Hardware] Volume polling started")
        
        while self._running:
            if self._pot is not None:
                current_volume = self.read_volume_percent()
                
                if current_volume >= 0:
                    # Only update if change exceeds threshold
                    if self._last_volume < 0 or abs(current_volume - self._last_volume) >= self.VOLUME_THRESHOLD:
                        if self.set_system_volume(current_volume):
                            self._last_volume = current_volume
                            print(f"[Hardware] Volume set to {current_volume}%")
            
            time.sleep(self.POLL_INTERVAL)
        
        print("[Hardware] Volume polling stopped")
    
    def start(self):
        """Start the hardware monitoring thread."""
        if self._running:
            return
        
        if self._pot is None and self._button is None:
            print("[Hardware] No hardware available, not starting monitor thread")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        print("[Hardware] Hardware controller started")
    
    def stop(self):
        """Stop the hardware monitoring thread."""
        self._running = False
        
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None
        
        if self._button is not None:
            self._button.close()
            self._button = None
        
        print("[Hardware] Hardware controller stopped")
    
    @property
    def is_available(self) -> bool:
        """Check if hardware is available."""
        return self._button is not None or self._pot is not None
