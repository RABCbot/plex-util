
# Plex FFMpeg utility

Python Flask webpage to query Plex library
and instantiate FFMPeg containers for specific transcoding jobs depending on the media format/audio/video codecs

## To build:
docker build -t plex-util .

## To instantiate container:
docker run -d -p 8080:8080 -e -v /var/run/docker.sock:/var/run/docker.sock -v /srv/dev-disk-by-uuid-XXXXXXXXXXXXXX/WDBlack/Docker/Plex-Util/config.json:/etc/config.json --name plex-util plex-util


