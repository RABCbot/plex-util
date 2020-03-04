import os
import requests
import xml.etree.ElementTree as ET
import subprocess
import logging

logging.basicConfig(filename='plex_stereo.log',level=logging.INFO)

plex_token = "<your-token>"
plex_url = "http://<your-ip>:32400/library/sections/1/all"
headers    = {"X-Plex-Token": plex_token,
              "Content-Type": "application/xml"}

def Transcode():
  response = requests.get(plex_url, headers=headers)
  response.raise_for_status()
  root = ET.fromstring(response.text)
  for video in root.findall("./Video/Media[@audioChannels='6'].."):
    part = video.find("./Media/Part")
    collection = video.find("Collection")
    if True: # collection is not None:
      if True: # collection.attrib["tag"] == "Transcode":
        file_split = os.path.splitext(part.attrib["file"])
        in_file = file_split[0] + file_split[1]
        out_file = file_split[0] + "_stereo" + file_split[1]
        logging.debug("Transcoding:", video.attrib["title"], in_file)
        if not os.path.exists(out_file):
          subprocess.call(["ffmpeg", "-i", in_file, "-ac", "2", "-af", "pan=stereo|FL=FC+0.30*FL+0.30*BL|FR=FC+0.30*FR+0.30*BR", "-c:v", "copy", out_file])


def CheckSubtitle():
  response = requests.get(plex_url, headers=headers)
  response.raise_for_status()
  root = ET.fromstring(response.text)
  for video in root.findall("./Video"):
    part = video.find("./Media/Part")
    file_split = os.path.splitext(part.attrib["file"])
    if not os.path.exists(file_split[0] + ".srt"):
      print(file_split)


CheckSubtitle()

