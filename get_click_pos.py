import time
import pyautogui

print("Click anywhere on the screen to get coordinates. Press Ctrl+C to exit.")

try:
    while True:
        x, y = pyautogui.position()  # Get current mouse position
        print(f'Coordinates: ({x}, {y})')
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\nExiting...")
