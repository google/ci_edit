import os

if 1:
  import subprocess

  def writeClipboard(output):
    process = subprocess.Popen(
              'pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
    process.communicate(output.encode('utf-8'))
  writeClipboard('does this work?')
  writeClipboard('also.')

  def readClipboard():
    return subprocess.check_output(
      'pbpaste', env={'LANG': 'en_US.UTF-8'}).decode('utf-8')
  print readClipboard()

if 0:
  from Tkinter import Tk
  r = Tk()
  r.withdraw()
  r.clipboard_clear()
  r.clipboard_append('i can has clipboardz?')
  print r.clipboard_get()
  r.update()
  r.destroy()
  print 'done'