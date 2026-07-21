import pyautogui
import time 


pyautogui.moveTo(100, 100, duration=1)  # Move the mouse to (100, 100) over 1 second
time.sleep(1)  # Wait for 1 second
pyautogui.click() 
pyautogui.rightClick()  # Click the mouse at the current position
pyautogui.scroll(100)  # Double click the mouse at the current position
