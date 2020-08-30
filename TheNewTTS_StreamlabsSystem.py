# TheNewTTS script for Streamlabs Chatbot
# Copyright (C) 2020 Luis Sanchez
#
# Versions:
#   - 2.0.0 08/29/2020 -
#       Added a say username before message option
#       Added a skip command
#       Fixed sometimes skipping messages
#       Fixed script stopped working suddenly  
#   - 1.2.1 12/09/2019 - Fixed Youtube/Mixer blacklist comparison against user ID instead of username
#   - 1.2.0 12/08/2019 - Added blacklist
#   - 1.1.0 12/03/2019 - Added max length in seconds
#   - 1.0.1 11/27/2019 - Fixed sound not playing
#   - 1.0.0 11/12/2019 - Initial release

# [Required] Import Libraries  #
import re
import os
import sys
import clr
import time
import json
import codecs

# Add script's folder to path to be able to find the other modules
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from tts_media import Media_Manager, run_cmd

# [Required] Script Information  #
Description = "Text to speech with Google translate voice"
ScriptName = "TheNewTTS"
Creator = "LuisSanchezDev"
Version = "1.2.1"
Website = "https://www.fiverr.com/luissanchezdev"

# Define Global Variables
global PATH,CONFIG_FILE, BLACKLIST_FILE
PATH = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE = os.path.join(PATH,"config.json")
BLACKLIST_FILE = os.path.join(PATH,"blacklist.db")
MAX_CHARACTERS_ALLOWED = 200

global SETTINGS, MEDIA_MGR, BLACKLIST
SETTINGS = {}
MEDIA_MGR = None
BLACKLIST = None

# [Required] Initialize Data (Only called on load)  #
def Init():
  global SETTINGS, PATH, CONFIG_FILE, BLACKLIST_FILE, BLACKLIST, MEDIA_MGR
  cache_folder = os.path.join(PATH, "cache")
  def ensure_cache_dir():
    if os.path.isdir(cache_folder):
      Parent.Log("TTS", "Deleting folder!")
      # os.system('RMDIR /Q/S "{0}"'.format(cache_folder))
      run_cmd('RMDIR /Q/S "{0}"'.format(cache_folder))
    os.mkdir(cache_folder)
  Parent.Log("TTS", "Deleting folder")
  while True:
    try:
      ensure_cache_dir()
      break
    except:
      continue

  try:
    with codecs.open(CONFIG_FILE, encoding="utf-8-sig", mode='r') as file:
      SETTINGS = json.load(file, encoding="utf-8-sig")
  except:
    SETTINGS = {
      "read_all_text": False,
      "say_username": True,
      "say_after_username": "says",
      "command": "!tts",
      "permission": "Everyone",
      "cooldown": 0,
      "user_cooldown": 0,
      "cost": 0,
      "msg_permission": "You don't have enough permissions to use this command.",
      "msg_cooldown": "This command is still on cooldown!",
      "msg_user_cooldown": "You need to wait before using this command again.",
      "msg_cost": "You don't have enough money!",
      "lang": "English (US) [en-US]",
      "pitch": 100,
      "speed": 100,
      "volume": 90,
      "length": 5,
      "cmd_ban": "!ttsban",
      "cmd_unban": "!ttsunban",
      "moderator_permission": "Caster",
      "cmd_skip": "!ttskip"
    }
  SETTINGS["lang"] = re.match(r"^.*\[(.+)\]", SETTINGS["lang"]).groups()[0]
  SETTINGS["pitch"] /= 100.0
  SETTINGS["speed"] /= 100.0
  SETTINGS["volume"] /= 100.0
  SETTINGS["_path"] = PATH
  SETTINGS["_cache"] = cache_folder
  
  # config.json backwards compatibility
  # Max tts length added
  if "length" not in SETTINGS: SETTINGS["length"] = 5

  # Blacklisting added
  if "cmd_ban" not in SETTINGS: SETTINGS["cmd_ban"] = "!ttsban"
  if "cmd_unban" not in SETTINGS: SETTINGS["cmd_unban"] = "!ttsunban"

  # Moderator commands added
  if "moderator_permission" not in SETTINGS: SETTINGS["moderator_permission"] = "Caster"
  if "cmd_skip" not in SETTINGS: SETTINGS["cmd_skip"] = "!ttskip"

  # Say username added
  if "say_username" not in SETTINGS: SETTINGS["say_username"] = True
  if "say_after_username" not in SETTINGS: SETTINGS["say_after_username"] = "says"
  
  BLACKLIST = Blacklist(BLACKLIST_FILE)
  MEDIA_MGR = Media_Manager(SETTINGS)

# [Required] Execute Data / Process messages  #
def Execute(data):
  global SETTINGS, MEDIA_MGR
  if data.IsChatMessage():
    command = data.GetParam(0)
    if Parent.HasPermission(data.User, SETTINGS["moderator_permission"], ""):
      target = data.GetParam(1)
      if command == SETTINGS["cmd_skip"]:
        MEDIA_MGR.skip()
        return
      elif command == SETTINGS["cmd_ban"]:
        if data.GetParamCount() != 2:
          Parent.SendStreamMessage("Usage: {0} <username>".format(SETTINGS["cmd_ban"]))
          return
        
        if BLACKLIST.add_user(target):
          Parent.SendStreamMessage(target + " successfully blacklisted!")
        else:
          Parent.SendStreamMessage(target + " already blacklisted!")          
        return
      elif command == SETTINGS["cmd_unban"]:
        if data.GetParamCount() != 2:
          Parent.SendStreamMessage("Usage: {0} <username>".format(SETTINGS["cmd_unban"]))
          return
        
        if BLACKLIST.remove_user(target):
          Parent.SendStreamMessage(target + " removed from blacklist!")
        else:
          Parent.SendStreamMessage(target + " was not blacklisted!")
        return
        

    if SETTINGS["read_all_text"]:
      if not BLACKLIST.is_user_blacklisted(data.UserName):
        text = data.Message
        if len(text) > MAX_CHARACTERS_ALLOWED:
          MEDIA_MGR.append(data.UserName + "'s message was too long")
        else:
          if SETTINGS["say_username"]:
            MEDIA_MGR.append(data.UserName + " " + SETTINGS["say_after_username"])
          MEDIA_MGR.append(text)
      return
    elif command == SETTINGS["command"]:
      if  not Parent.HasPermission(data.User, SETTINGS["permission"], ""):
        Parent.SendStreamMessage(SETTINGS["msg_permission"])
        return
      if BLACKLIST.is_user_blacklisted(data.UserName):
        Parent.SendStreamMessage(data.User + " is blacklisted!")
        return
      if SETTINGS["user_cooldown"] and Parent.GetUserCooldownDuration(ScriptName, SETTINGS["command"], data.User):
        Parent.SendStreamMessage(SETTINGS["msg_user_cooldown"])
        return
      if SETTINGS["cooldown"] and Parent.GetCooldownDuration(ScriptName, SETTINGS["command"]):
        Parent.SendStreamMessage(SETTINGS["msg_cooldown"])
        return
      if not Parent.RemovePoints(data.User, data.UserName, SETTINGS["cost"]):
        Parent.SendStreamMessage(SETTINGS["msg_cost"])
        return
      if not data.GetParam(1):
        Parent.SendStreamMessage("You need to specify a message")
        return
      text = " ".join(data.Message.split(' ')[1:])
      if len(text) > MAX_CHARACTERS_ALLOWED:
        Parent.AddPoints(data.User, data.UserName, SETTINGS["cost"])
        Parent.SendStreamMessage("Can't read message because the text istoo long!")
        return
      else:
        if SETTINGS["say_username"]:
          MEDIA_MGR.append(data.UserName + " " + SETTINGS["say_after_username"])
        MEDIA_MGR.append(text)
      Parent.AddCooldown(ScriptName, SETTINGS["command"], SETTINGS["cooldown"])
      Parent.AddUserCooldown(ScriptName, SETTINGS["command"], data.User, SETTINGS["user_cooldown"])
      return

# [Required] Tick method (Gets called during every iteration even when there is no incoming data)  #
def Tick():
  pass

# [Optional] Reload Settings (Called when a user clicks the Save Settings button in the Chatbot UI)  #
def ReloadSettings(jsonData):
  global MEDIA_MGR
  Unload()
  Init()
  MEDIA_MGR.append("Configuration updated successfully")

# Unload (Called when a user reloads their scripts or closes the bot / cleanup stuff)
def Unload():
  global MEDIA_MGR
  if MEDIA_MGR:
    # Parent.Log("TTS", "Closing media manager")
    MEDIA_MGR.close()
    del MEDIA_MGR
    # Parent.Log("TTS", "Media manager closed!")
    # MEDIA_MGR = None


class Blacklist:
  def __init__(self, file_path):
    self._path = file_path
  def add_user(self, user_name):
    user_name = Blacklist._strip_username(user_name)
    if self.is_user_blacklisted(user_name): return False
    db = self._load()
    db.append(user_name)
    self._save(db)
    return True
  
  def remove_user(self, user_name):
    user_name = Blacklist._strip_username(user_name)
    if not self.is_user_blacklisted(user_name): return False
    db = self._load()
    db.remove(user_name)
    self._save(db)
    return True

  def is_user_blacklisted(self, user_name):
    user_name = Blacklist._strip_username(user_name)
    if user_name in self._load(): return True
    return False

  def _load(self):
    if not os.path.isfile(self._path): return []
    with codecs.open(self._path, encoding="utf-8-sig", mode='r') as file:
      return json.load(file, encoding="utf-8-sig")
  def _save(self, modified_db):
    with codecs.open(self._path, encoding="utf-8-sig", mode='w') as file:
      file.write(json.dumps(modified_db, encoding="utf-8-sig"))
  @staticmethod
  def _strip_username(user_name):
    user_name = user_name.lower()
    if "@" in user_name:
      user_name = user_name.replace("@","")
    return user_name


# [TheNewTTS] UI Link buttons  #
def donate():
  os.startfile("https://streamlabs.com/luissanchezdev/tip")
def open_contact_me():
  os.startfile("www.fiverr.com/luissanchezdev/makea-custom-streamlabs-chatbot-script")
def open_contact_td():
  os.startfile("https://www.fiverr.com/tecno_diana/make-cute-twich-emote-for-your-stream")
def open_readme():
  os.startfile("https://github.com/LuisSanchez-Dev/TheNewTTS")