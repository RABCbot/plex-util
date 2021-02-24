import os
import urllib3
import xml.etree.ElementTree as ET
import subprocess
import logging
from flask import Flask, render_template
from datetime import datetime
import json
import docker

logger = logging.getLogger()

app = Flask(__name__)

plex_token = os.environ["PLEX_TOKEN"]
plex_url = os.environ["PLEX_URL"]
plex_movies = os.getenv("PLEX_MOVIES_LIBRARY", 1)
docker_url = os.getenv("DOCKER_URL", 'unix://var/run/docker.sock')
ffmpeg_image = os.getenv("FFMPEG_IMAGE", "linuxserver/ffmpeg")
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
  containers = ET.fromstring(r.data.decode('utf-8'))

  videos = []
  for video in containers.findall("./Video"):
    videos.append(get_video(video.attrib["ratingKey"]))

  return render_template("movies.html", videos=videos)

# Return a JSON representation of the video container
def get_video(key):
  http = urllib3.PoolManager()
  r = http.request('GET', 
        f"{plex_url}/library/metadata/{key}", 
        headers={"X-Plex-Token": plex_token, "Content-Type": "application/xml"})
  container = ET.fromstring(r.data.decode('utf-8'))
  video = container.find("./Video")
  dur = datetime.fromtimestamp(int(video.attrib["duration"])/1000.0)
  data = {
          "key": key,
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

  return data

@app.route("/transcode/", methods=["GET"])
@app.route("/transcode/<key>", methods=["GET"])
def transcode(key=None):

  client = docker.DockerClient(base_url=docker_url)
  containers = client.containers.list(filters={"ancestor":ffmpeg_image})

  # if key, run new ffmpeg container if not running already
  if key is not None:
    # check if already running
    lst = [c for c in containers if c.name == key]
    if len(lst) == 0:
      video = get_video(key)
      src = video["filename"]
      dst = f"/media/Transcoded/{key}.mkv"
      cmd = f"-i {src} -ac 2 -af pan=stereo|FL=FC+0.30*FL+0.30*BL|FR=FC+0.30*FR+0.30*BR -c:v copy {dst}"
      container = client.containers.run(image=ffmpeg_image,
        command=cmd,
        name=key,
        labels={"Title":video["title"]},
        auto_remove=True,
        detach=True,
        volumes={"/srv/dev-disk-by-uuid-710d520b-bb51-4d6e-8c51-f4b9d8126a08/WDBlack/Media":{"bind":"/media","mode":"rw"}})
      containers.append(container)

  return render_template("transcode.html", containers=containers)

if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0", port=8080)
