
# Plex FFMpeg utility

docker build -t plex-util .

docker run -d -p 8080:8080 -v /var/run/docker.sock:/var/run/docker.sock -v /<local-path>/config.json:/etc/config.json --name plex-util plex-util


