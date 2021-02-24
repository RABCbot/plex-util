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
plex_movies = os.getenv("PLEX_MOVIES_LIBRARY", 1)
ok = {"status": "ok"}

@app.route("/about/")
def about():
  return render_template("about.html")

@app.route("/status", methods=["GET"])
def status():
  return json.dumps(ok)

@app.route("/movies")
def movies():
  http = urllib3.PoolManager()

  r = http.request('GET', 
        f"{plex_url}/library/sections/{plex_movies}/all", 
        headers={"X-Plex-Token": plex_token, "Content-Type": "application/xml"})
  root = ET.fromstring(r.data.decode('utf-8'))

  videos = []
  for video in root.findall("./Video"):
    url = video.attrib["key"]
    url = f"{plex_url}{url}"
    r = http.request('GET', 
        url, 
        headers={"X-Plex-Token": plex_token, "Content-Type": "application/xml"})
    dur = datetime.fromtimestamp(int(video.attrib["duration"])/1000.0)
    data = {
            "title": video.attrib["title"],
            "genre": "",
            "year": "",
            "played": "0",
            "rating": "",
            "score": "",
            "duration": dur.strftime("%H:%M"),
            "videoCodec": "",
            "videoDepth": "",
            "audioCodec": "",
            "audioChannels": "",
            "subtitle": "",
            "filename": video[0][0].attrib["file"]
          }
    genre = video.find("./Genre")
    if genre is not None:
      data["genre"] = genre.attrib["tag"]
    if "year" in video.attrib:
      data["year"] = video.attrib["year"]
    if "viewCount" in video.attrib:
      data["played"] = video.attrib["viewCount"]
    if "contentRating" in video.attrib:
      data["rating"] = video.attrib["contentRating"]
    if "audienceRating" in video.attrib:
      data["score"] = video.attrib["audienceRating"]

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

  return render_template("movies.html", videos=videos)

@app.route("/transcode/", methods=["GET"])
def transcode():
  return render_template("transcode.html")

if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0", port=8080)
