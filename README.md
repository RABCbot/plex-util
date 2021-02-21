# plex-util
Python Flask app to query Plex library and run ffmpeg transcode

## Run as a docker container
```
docker build -t plex-util .
docker run -d -p 8080:8080 -e PLEX_URL=http://<plex-server-ip>:32400 -e PLEX_TOKEN=<plex-server-tocken> --name plex-util plex-util
```

Open http://<docker-ip>:8080/library

