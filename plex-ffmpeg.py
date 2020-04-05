
import os
import requests
import xml.etree.ElementTree as ET
import subprocess
import logging
from flask import Flask
from datetime import datetime
import json

app = Flask(__name__)
logging.basicConfig(filename="plex_stereo.log",level=logging.DEBUG)

plex_token = "<your-plex-token>"
plex_url = "http://<your-plex-server-ip>:32400/library/sections/1/all"
headers    = {"X-Plex-Token": plex_token,
              "Content-Type": "application/xml"}
ok = {"status": "ok"}

@app.route("/status", methods=["GET"])
def status():
  return json.dumps(ok)


@app.route("/transcode", methods=["GET"])
def transcode():
  response = requests.get(plex_url, headers=headers)
  response.raise_for_status()
  root = ET.fromstring(response.text)
  for video in root.findall("./Video/Media[@audioChannels='6'].."):
    part = video.find("./Media/Part")
    collection = video.find("Collection")
    if True: # collection is not None:
      if True: # collection.attrib["tag"] == "Transcode":
        file_split = os.path.splitext(part.attrib['file'])
        in_file = file_split[0] + file_split[1]
        out_file = file_split[0] + "_stereo" + file_split[1]
        logging.info("Transcoding:", video.attrib["title"], in_file)
        if not os.path.exists(out_file):
          subprocess.call(["ffmpeg", "-i", in_file, "-ac", "2", "-af", "pan=stereo|FL=FC+0.30*FL+0.30*BL|FR=FC+0.30*FR+0.30*BR", "-c:v", "copy", out_file])
  return json.dumps(ok)


@app.route("/subtitle", methods=["GET"])
def get_subtitle():
  response = requests.get(plex_url, headers=headers)
  response.raise_for_status()
  root = ET.fromstring(response.text)
  titles, files, added = [], [], []
  for video in root.findall("./Video"):
    part = video.find("./Media/Part")
    file_split = os.path.splitext(part.attrib["file"])
    if not os.path.exists(file_split[0] + ".srt"):
      # print(video.attrib["title"], "\t", part.attrib["file"])
      titles.append(video.attrib["title"])
      added.append(datetime.fromtimestamp(int(video.attrib["addedAt"])).strftime('%Y-%m-%d'))
      files.append(part.attrib["file"])
  titles_files = [{"title": t, "added": a, "file": f} for t, a, f in zip(titles, added, files)]
  return json.dumps(titles_files)

if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0", port=8080)
