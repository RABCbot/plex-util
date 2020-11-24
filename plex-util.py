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
plex_url = "http://<your-plex-ip>:32400/library/sections/1/all"
headers    = {"X-Plex-Token": plex_token,
              "Content-Type": "application/xml"}
ok = {"status": "ok"}

@app.route("/status", methods=["GET"])
def status():
  return json.dumps(ok)

@app.route("/help", methods=["GET"])
def help():
  msg = "<b>GET /status</b><br/>" \
        "<b>GET /transcode</b> transcode 6-audio titles to stereo<br/>" \
        "<b>GET /get_subtitle/true</b> returns titles with subs<br/>" \
        "<b>GET /get_subtitle/false</b> returns titles without subs<br/>" \
        "<b>GET /get_list</b> returns all titles<br/>" \
        "Runs as a service using systemctl plex-util<br/>"
  return msg

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

@app.route("/get_subtitle/<option>", methods=["GET"])
def get_subtitle(option):
  response = requests.get(plex_url, headers=headers)
  response.raise_for_status()
  root = ET.fromstring(response.text)
  titles, files, added = [], [], []
  msg = ""
  for video in root.findall("./Video"):
    media = video.find("./Media")
    part = video.find("./Media/Part")
    file_split = os.path.splitext(part.attrib["file"])
    exists = os.path.exists(file_split[0] + ".srt")

    if (exists and option == "true") or (not exists and option == "false"):

      # print(video.attrib["title"], "\t", part.attrib["file"])
      t = video.attrib["title"]
      titles.append(t)
      dt = datetime.fromtimestamp(int(video.attrib["addedAt"])).strftime('%Y-%m-%d')
      added.append(dt)
      f = part.attrib["file"]
      files.append(f)
      ch = ""
      if "audioChannels" in media.attrib: ch = media.attrib["audioChannels"]
      msg += "{}&emsp;Added: {}&emsp; Audio: {}&emsp; Path: {}<br/>".format(t, dt, ch, f)

  # titles_files = [{"title": t, "added": a, "file": f} for t, a, f in zip(titles, added, files)]

  return msg

if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0", port=8080)

