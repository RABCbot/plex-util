import os
import requests
import xml.etree.ElementTree as ET
import subprocess
import logging
from flask import Flask
import json

api = Flask(__name__)
logging.basicConfig(filename='plex_stereo.log',level=logging.DEBUG)

plex_token = "<your plex token>"
plex_url = "http://<your pelx server>:32400/library/sections/1/all"
headers    = {"X-Plex-Token": plex_token,
              "Content-Type": "application/xml"}
ok = [{"ok"}]

@api.route('/transcode', methods=['GET'])
def transcode():
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
        logging.info("Transcoding:", video.attrib["title"], in_file)
        if not os.path.exists(out_file):
          subprocess.call(["ffmpeg", "-i", in_file, "-ac", "2", "-af", "pan=stereo|FL=FC+0.30*FL+0.30*BL|FR=FC+0.30*FR+0.30*BR", "-c:v", "copy", out_file])
  return json.dumps(ok)


@api.route('/subtitle', methods=['GET'])
def get_subtitle():
  response = requests.get(plex_url, headers=headers)
  response.raise_for_status()
  root = ET.fromstring(response.text)
  titles, files = [], []
  for video in root.findall("./Video"):
    part = video.find("./Media/Part")
    file_split = os.path.splitext(part.attrib["file"])
    if not os.path.exists(file_split[0] + ".srt"):
      # print(video.attrib["title"], "\t", part.attrib["file"])
      titles.append(video.attrib["title"])
      files.append(part.attrib["file"])
  titles_files = [{"title": t, "file": f} for t, f in zip(titles, files)]
  return json.dumps(titles_files)

if __name__ == '__main__':
    api.run(host='0.0.0.0', port=8080)

