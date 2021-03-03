import os
import urllib3
import xml.etree.ElementTree as ET
import subprocess
import logging
from flask import Flask, render_template
from datetime import datetime
import json
import docker

logging_level = os.getenv('LOGGING', logging.INFO)
logger = logging.getLogger()
logger.setLevel(logging_level)

app = Flask(__name__)

ok = {"status": "ok"}

@app.route("/about/")
def about():
  return render_template("about.html")

@app.route("/status", methods=["GET"])
def status():
  return json.dumps(ok)

# Render a page with all the movies
@app.route("/movies")
def movies():
  cfg = read_config()
  url = cfg["plex"]["url"]
  library = cfg["plex"]["library"]
  token = cfg["plex"]["token"]

  http = urllib3.PoolManager()
  r = http.request('GET', 
        f"{url}/library/sections/{library}/all", 
        headers={"X-Plex-Token": token, "Content-Type": "application/xml"})
  container = ET.fromstring(r.data.decode('utf-8'))

  videos = []
  for video in container.findall("./Video"):
    videos.append(get_video(video.attrib["ratingKey"]))

  return render_template("movies.html", videos=videos)

# Return a JSON representation of the Plex video container
def get_video(key):
  cfg = read_config()
  url = cfg["plex"]["url"]
  token = cfg["plex"]["token"]

  http = urllib3.PoolManager()
  r = http.request('GET', 
        f"{url}/library/metadata/{key}", 
        headers={"X-Plex-Token": token, "Content-Type": "application/xml"})
  container = ET.fromstring(r.data.decode('utf-8'))
  data = {
          "key": "",
          "title": "",
          "genre": "",
          "year": "",
          "played": "0",
          "rating": "",
          "score": "",
          "duration": "",
          "videoResolution": "",
          "videoCodec": "",
          "videoDepth": "",
          "audioCodec": "",
          "audioChannels": "",
          "format": "",
          "subtitle": "",
          "profiles": [],
          "filename": ""
        }

  video = container.find("./Video")
  data["key"] = video.attrib["ratingKey"]
  data["title"] = video.attrib["title"]
  dur = datetime.utcfromtimestamp(int(video.attrib["duration"])/1000.0)
  data["duration"] = dur.strftime("%-I:%M")
  if "year" in video.attrib:
    data["year"] = video.attrib["year"]
  if "viewCount" in video.attrib:
    data["played"] = video.attrib["viewCount"]
  if "contentRating" in video.attrib:
    data["rating"] = video.attrib["contentRating"]
  if "audienceRating" in video.attrib:
    data["score"] = video.attrib["audienceRating"]

  genre = video.find("./Genre")
  if genre is not None:
    data["genre"] = genre.attrib["tag"]

  media = video.find("./Media")
  data["format"] = media.attrib["container"]
  data["videoResolution"] = "{}x{}".format(media.attrib["width"], media.attrib["height"])

  part = media.find("./Part")
  data["filename"] = part.attrib["file"]

  stream = part.find("./Stream[@streamType='1']")
  if stream is not None:
    data["videoCodec"] = stream.attrib["codec"]
    data["videoDepth"] = stream.attrib["bitDepth"]

  stream = part.find("./Stream[@streamType='2']")
  if stream is not None:
    data["audioCodec"] = stream.attrib["codec"]
    if "profile" in stream.attrib:
      data["audioCodec"] = stream.attrib["profile"]
    data["audioChannels"] = stream.attrib["channels"]

  stream = part.find("./Stream[@streamType='3']")
  if stream is not None:
    data["subtitle"] = stream.attrib["displayTitle"]

  data["profiles"] = ffmpeg_profiles(data)

  return data

# Render a page with current FFmpeg containers and optional creates a new container
@app.route("/transcode/", methods=["GET"])
@app.route("/transcode/<key>/<profile>/", methods=["GET"])
def transcode(key=None, profile=None):
  try:
    cfg = read_config()
    ffmpeg_output = cfg["ffmpeg"]["output"]

    client = docker.DockerClient(base_url=cfg["ffmpeg"]["docker_url"])
    containers = client.containers.list(all=True, filters={"ancestor":cfg["ffmpeg"]["docker_image"]})


    # if a key provided, create a new ffmpeg container if does not exists already
    if key is not None:
      container_name = f"ffmpeg{key}"
      lst = [container for container in containers if container.name == container_name]
      if len(lst) == 0:
        video = get_video(key)
        src = video["filename"]
        _, dst = os.path.split(src)
        dst = f"{ffmpeg_output}{dst}"
        container = client.containers.run(image=cfg["ffmpeg"]["docker_image"],
          command=ffmpeg_command(profile).format(src, dst),
          name=container_name,
          labels={"title":video["title"],"created":datetime.now().strftime("%Y/%m/%d %H:%M:%S"),"profile":profile},
          auto_remove=cfg["ffmpeg"]["auto_remove"],
          detach=True,
          volumes={cfg["ffmpeg"]["media"]:{"bind":"/media","mode":"rw"}})
        containers.append(container)
    return render_template("transcode.html", containers=containers)

  except Exception as ex:
    return render_template("exception.html", error=f"transcode failed because: {ex}")

# Return all the matching ffmpeg commands by video codecs
def ffmpeg_profiles(video):
  cfg = read_config()
  lst = [p for p in cfg["profiles"] if video["format"] in p["format"] or p["videoCodec"] == video["videoCodec"] and str(p["videoDepth"]) == video["videoDepth"] and str(p["audioChannels"]) == video["audioChannels"] and not(cfg["plex"]["hide_profile_if_played"] and video["played"] != "0")]
  return lst

# Return the matching ffmpeg command by profile
def ffmpeg_command(name):
  cfg = read_config()
  profile = [p for p in cfg["profiles"] if p["name"] == name][0]
  return profile["command"]

def read_config():
  with open("/etc/config.json", "r") as f:
    return json.load(f)

if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0", port=8080)
