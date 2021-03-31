
# Plex FFMpeg utility

docker build -t plex-util .

docker run -d -p 8080:8080 -e -v /var/run/docker.sock:/var/run/docker.sock -v /srv/dev-disk-by-uuid-710d520b-bb51-4d6e-8c51-f4b9d8126a08/WDBlack/Docker/Plex-Util/config.json:/etc/config.json --name plex-util plex-util


