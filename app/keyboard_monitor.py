import app.log
from pynput import keyboard

class KeyboardListener:
  """
  This class is used to listen to the user's inputs in order to detect any
  modifier keys being used. Due to limitations of this library, errors may occur
  when running over ssh, since an X server is required. This will also not be
  able to detect most keys on macOS unless run as root. See more details at
  https://pynput.readthedocs.io/en/latest/limitations.html.
  """
  def __init__(self):
    self.listener = keyboard.Listener(on_press=self.onPress, on_release=self.onRelease)
    self.keys_pressed = set()
    self.keys_to_check = {keyboard.Key.ctrl, keyboard.Key.backspace}

  def onPress(self, key):
    if key in self.keys_to_check:
      self.keys_pressed.add(key)
      app.log.info(key, "has been inserted into KeyboardListener.")

  def onRelease(self, key):
    if key in self.keys_pressed:
      self.keys_pressed.remove(key)
      app.log.info(key, "has been released from KeyboardListener.")

  def start(self):
    self.listener.start()

  def stop(self):
    self.listener.stop()

class KeyboardMonitor:
  """
  This class is used to monitor the user's inputs in order to detect any
  modifier + key combinations.
  """
  def __init__(self):
    self.listener = KeyboardListener()

  def start(self):
    self.listener.start()

  def getKeysPressed(self):
    return self.listener.keys_pressed
