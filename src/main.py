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

plex_token = os.environ["PLEX_TOKEN"]
plex_url = os.environ["PLEX_URL"]
plex_movies = os.getenv("PLEX_MOVIES_LIBRARY", 1)

docker_url = os.getenv("DOCKER_URL", 'unix://var/run/docker.sock')
docker_auto_remove = False
ffmpeg_image = os.getenv("FFMPEG_IMAGE", "linuxserver/ffmpeg")
ffmpeg_media = os.environ["FFMPEG_MEDIA"]
ffmpeg_output = os.getenv("FFMPEG_OUTPUT", "/media/Transcoded/")

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
  http = urllib3.PoolManager()
  r = http.request('GET', 
        f"{plex_url}/library/sections/{plex_movies}/all", 
        headers={"X-Plex-Token": plex_token, "Content-Type": "application/xml"})
  containers = ET.fromstring(r.data.decode('utf-8'))

  videos = []
  for video in containers.findall("./Video"):
    videos.append(get_video(video.attrib["ratingKey"]))

  return render_template("movies.html", videos=videos)

# Return a JSON representation of the Plex video container
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
          "transcode": [],
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

  data["transcode"] = ffmpeg_matching(data)

  return data

# Render a page with current FFmpeg containers and optional creates a new container
@app.route("/transcode/", methods=["GET"])
@app.route("/transcode/<key>/<name>/", methods=["GET"])
def transcode(key=None, name=None):
  try:
    client = docker.DockerClient(base_url=docker_url)
    containers = client.containers.list(all=True, filters={"ancestor":ffmpeg_image})

    # if a key provided, create a new ffmpeg container if does not exists already
    if key is not None:
      c_name = f"ffmpeg{key}"
      lst = [c for c in containers if c.name == c_name]
      if len(lst) == 0:
        video = get_video(key)
        src = video["filename"]
        _, dst = os.path.split(src)
        dst = f"{ffmpeg_output}{dst}"
        container = client.containers.run(image=ffmpeg_image,
          command=ffmpeg_command(name).format(src, dst),
          name=c_name,
          labels={"title":video["title"],"created":datetime.now().strftime("%Y/%m/%d %H:%M:%S")},
          auto_remove=docker_auto_remove,
          detach=True,
          volumes={ffmpeg_media:{"bind":"/media","mode":"rw"}})
        containers.append(container)
    return render_template("transcode.html", containers=containers)

  except Exception as ex:
    return render_template("exception.html", error=f"transcode failed because: {ex}")

# Return all the matching ffmpeg commands by video codecs
def ffmpeg_matching(video):
  with app.open_resource("static/ffmpeg.json") as f:
    cmds = json.load(f)
  lst = [cmd for cmd in cmds if cmd["videoCodec"] == video["videoCodec"] and str(cmd["videoDepth"]) == video["videoDepth"] and str(cmd["audioChannels"]) == video["audioChannels"]]
  return lst

# Return the matching ffmpeg command by name
def ffmpeg_command(name):
  with app.open_resource("static/ffmpeg.json") as f:
    cmds = json.load(f)
  cmd = [cmd for cmd in cmds if cmd["name"] == name][0]
  return cmd["command"]

if __name__ == "__main__":
    app.debug = True
    app.run(host="0.0.0.0", port=8080)
