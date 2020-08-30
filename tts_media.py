# Library for TheNewTTS script for Streamlabs Chatbot
# Copyright (C) 2020 Luis Sanchez

import os
import clr
import time 
import threading

# Required to download the audio files
clr.AddReference("System.Web")
from System.Web import HttpUtility
from System.Net import WebClient

# Required to run cmd commands without a window and wait for the result
from System.Diagnostics import Process, ProcessStartInfo, ProcessWindowStyle

# Required to play audio files
clr.AddReference("NAudio")
import NAudio
from NAudio.Wave import AudioFileReader, WaveOutEvent, PlaybackState

global player_closed, downloader_closed
player_closed  = False
downloader_closed = False
global close_player, close_downloader
close_player= False
close_downloader= False

class Media_Manager:
  def __init__(self, settings):
    self._downloader = Media_Downloader(settings)
    self._player = Media_Player(self._downloader, settings)
  def skip(self):
    self._player.skip_current = True
  def append(self, text):
    self._downloader.append(text)
  def reload(self):
    self.close()
    self.__init__(self._sett  )
  def close(self):
    global player_closed, downloader_closed 
    global close_player, close_downloader
    # self._player.close()
    # self._downloader.close()
    close_player = True
    close_downloader = True
    # get_parent().Log("Manager", "Waiting for threads...")
    self._player._thread.join()    
    self._downloader._thread.join()    
    while not player_closed and not downloader_closed:
      time.sleep(0.05)
    close_player = False
    close_downloader = False
    player_closed = False
    downloader_closed = False
    # get_parent().Log("Manager", "Both closed")
class Media_Player:
  def __init__(self, media_downloader, settings):
    self.media_downloader = media_downloader
    self._settings = settings
    self._thread = threading.Thread(target=self._play_loop)
    self._thread.start()
    self.skip_current = False
    self._exit = False
  def close(self):
    self._exit = True
    self._thread.join()
  def _play_loop(self):
    global close_player, player_closed
    try:
      while True:
        if close_player:
          player_closed = True
          raise ValueError
        if len(self.media_downloader.queue) > 0:
          started_playing = time.time()
          next_tts_path = self.media_downloader.queue.pop(0)
          with AudioFileReader(next_tts_path) as reader:
            with WaveOutEvent() as device:
              device.Init(reader)
              device.Play()
              self.skip_current = False
              while device.PlaybackState == PlaybackState.Playing:
                if close_player:
                  player_closed = True
                  raise ValueError
                if self.skip_current:
                  self.skip_current = False
                  break
                elapsed = time.time() - started_playing
                if elapsed >= self._settings["length"]:
                  break
                time.sleep(0.1)
          run_cmd('del "{0}"'.format(next_tts_path))
        else:
          time.sleep(0.150)
    except Exception as e:
      player_closed = True
      raise ValueError
class Media_Downloader:
  def __init__(self, settings):
    self._settings = settings
    self._queue = []
    self._count = 0
    self._thread = threading.Thread(target=self._download_async)
    self._thread.start()
    self.queue = []
    self._exit = False
  def close(self):
    self._exit = True
    self._thread.join()
  def append(self, text):
    self._queue.append(text)
  def _download_async(self):
    global close_downloader, downloader_closed
    try:
      while True:
        if close_downloader:
          downloader_closed = True
          raise ValueError
        if len(self._queue) > 0:
          text = self._queue.pop(0)
          file_path = os.path.join(self._settings["_cache"], str(self._count) + ".mp3")
          try:
            download_tts(file_path, text, self._settings)
            if close_downloader:
              downloader_closed = True
              raise ValueError
            process_tts(file_path, self._settings)
            self.queue.append(file_path)
            self._count += 1
          except Exception as e:
            get_parent().Log("Media_Downloader", "There was an error downloading this text\n" + str(e))
        time.sleep(0.150)
    except Exception as e:
      # get_parent().Log("Download thread", str(e))
      # get_parent().Log("Download thread", str(self.__dict__))
      downloader_closed = True
      raise ValueError
# [TheNewTTS] Download from Google Translate voice generator using defined TTS language  #
def download_tts(file_path, text, settings):
  with WebClient() as wc:
    url = "https://translate.google.com/translate_tts?ie=UTF-8&tl={1}&client=tw-ob&q={0}".format(
      HttpUtility.UrlEncode(text), settings["lang"]
    )
    wc.Headers["Referer"] = "http://translate.google.com/"
    wc.Headers["User-Agent"] = "stagefright/1.2 (Linux;Android 5.0)"
    wc.DownloadFile(url, file_path)

# [TheNewTTS] Changes the pitch, speed and volume of downloaded mp3  #
def process_tts(file_path, settings):
  temp_mp3 = os.path.join(os.path.dirname(file_path), "processing.mp3")
  commands = [
    'cd "{0}"'.format(settings["_path"]),
    'ffmpeg.exe -t {0} -i "{1}" -af asetrate=24000*{2},atempo={3}/{2},aresample=48000,volume={4} "{5}" -y'.format(
      settings["length"],
      file_path,
      settings["pitch"],
      settings["speed"],
      settings["volume"],
      temp_mp3  
    ),
    'del "{0}"'.format(file_path),
    'move "{0}" "{1}"'.format(temp_mp3, file_path)
  ]
  run_cmd(" & ".join(commands))

def run_cmd(command):
  # os.system(command)
  pinfo = ProcessStartInfo()
  pinfo.FileName = "cmd.exe"
  pinfo.WindowStyle = ProcessWindowStyle.Hidden;
  pinfo.Arguments = "/C" + command
  cmd = Process.Start(pinfo)
  cmd.WaitForExit()   

import System
clr.AddReference([asbly for asbly in System.AppDomain.CurrentDomain.GetAssemblies() if "AnkhBotR2" in str(asbly)][0])
import AnkhBotR2
def get_parent():
  return AnkhBotR2.Managers.PythonManager()