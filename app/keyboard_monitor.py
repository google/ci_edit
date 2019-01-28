import app.log
from pynput import keyboard

class KeyboardListener:
  """
  This class is used to listen to the user's inputs in order to detect any
  modifier keys being used.
  """
  def __init__(self):
    self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
    self.keys_pressed = set()
    self.modifiers_to_check = {keyboard.Key.ctrl}

  def on_press(self, key):
    if key in self.modifiers_to_check:
      self.keys_pressed.add(key)
      app.log.info(key, "has been inserted into KeyboardListener.")

  def on_release(self, key):
    try:
      self.keys_pressed.remove(key)
      app.log.info(key, "has been released from KeyboardListener.")
    except KeyError as e:
      pass

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
