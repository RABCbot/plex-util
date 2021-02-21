import os
import urllib3
import xml.etree.ElementTree as ET
import subprocess
import logging
from flask import Flask, render_template
from datetime import datetime
import json

app = Flask(__name__)
logging.basicConfig(filename="plex_stereo.log",level=logging.DEBUG)

plex_token = os.environ["PLEX_TOKEN"]
plex_url = os.environ["PLEX_URL"]
plex_library = os.getenv("PLEX_LIBRARY", 1)
ok = {"status": "ok"}

@app.route("/")
def home():
  return render_template("home.html")

@app.route("/about/")
def about():
  return render_template("about.html")

@app.route("/status", methods=["GET"])
def status():
  return json.dumps(ok)

@app.route("/help", methods=["GET"])
def help():
  msg = "<b>GET /status</b><br/>" \
        "<b>GET /library</b>Returns all the library<br/>" \
        "<b>GET /highres</b>Returns HVEC/10bits/5.1 library<br/>" \
        "<b>GET /get_subtitle/false</b> returns titles without subs<br/>" \
        "<b>GET /get_list</b> returns all titles<br/>" \
        "Runs as a service using systemctl plex-util<br/>"
  return msg

@app.route("/library")
def library():
  http = urllib3.PoolManager()

  r = http.request('GET', 
        f"{plex_url}/library/sections/{plex_library}/all", 
        headers={"X-Plex-Token": plex_token, "Content-Type": "application/xml"})
  root = ET.fromstring(r.data.decode('utf-8'))

  videos = []
  for video in root.findall("./Video"):
    url = video.attrib["key"]
    url = f"{plex_url}{url}"
    r = http.request('GET', 
        url, 
        headers={"X-Plex-Token": plex_token, "Content-Type": "application/xml"})
    data = {
            "title": video.attrib["title"],
            "year": "",
            "duration": int(video.attrib["duration"]) / 3600000,
            "videoCodec": "",
            "videoDepth": "",
            "audioCodec": "",
            "audioChannels": "",
            "subtitle": "",
            "filename": video[0][0].attrib["file"]
          }
    if "year" in video.attrib:
      data["year"] = video.attrib["year"]

    container = ET.fromstring(r.data.decode('utf-8'))
    stream = container.find("./Video/Media/Part/Stream[@streamType='1']")
    if stream is not None:
      data["videoCodec"] = stream.attrib["codec"]
      data["videoDepth"] = stream.attrib["bitDepth"]

    stream = container.find("./Video/Media/Part/Stream[@streamType='2']")
    if stream is not None:
      data["audioCodec"] = stream.attrib["codec"]
      data["audioChannels"] = stream.attrib["channels"]

    stream = container.find("./Video/Media/Part/Stream[@streamType='3']")
    if stream is not None:
      data["subtitle"] = stream.attrib["displayTitle"]
    videos.append(data)

  return render_template("library.html", videos=videos)

@app.route("/highres")
def highres():
  http = urllib3.PoolManager()

  r = http.request('GET', 
        f"{plex_url}/library/sections/{plex_library}/all", 
        headers={"X-Plex-Token": plex_token, "Content-Type": "application/xml"})
  root = ET.fromstring(r.data.decode('utf-8'))

  videos = []
  for video in root.findall("./Video/Media[@audioChannels='6']..") + root.findall("./Video/Media[@videoCodec='hvec'].."):
    url = video.attrib["key"]
    url = f"{plex_url}{url}"
    r = http.request('GET', 
        url, 
        headers={"X-Plex-Token": plex_token, "Content-Type": "application/xml"})
    container = ET.fromstring(r.data.decode('utf-8'))
    stream1 = container.find("./Video/Media/Part/Stream[@streamType='1']")
    stream2 = container.find("./Video/Media/Part/Stream[@streamType='2']")
    stream3 = container.find("./Video/Media/Part/Stream[@streamType='3']")
    subtitle = ""
    if stream3 is not None:
      subtitle = stream3.attrib["displayTitle"]
    videos.append({"videoCodec": stream1.attrib["codec"],
                   "videoBits": stream1.attrib["bitDepth"],
                   "audioCodec": stream2.attrib["codec"],
                   "audioChannels": stream2.attrib["channels"],
                   "subtitle": subtitle,
                   "filename": video[0][0].attrib["file"]})

  return(json.dumps(videos))

@app.route("/transcode", methods=["GET"])
def transcode():
  http = urllib3.PoolManager()
  r = http.request('GET', 
        plex_url, 
        headers={"X-Plex-Token": plex_token, "Content-Type": "application/xml"})
  root = ET.fromstring(r.data.decode('utf-8'))

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
  http = urllib3.PoolManager()
  r = http.request('GET', 
        plex_url, 
        headers={"X-Plex-Token": plex_token, "Content-Type": "application/xml"})
  root = ET.fromstring(r.data.decode('utf-8'))

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
