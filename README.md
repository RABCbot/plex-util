
# Plex FFMpeg utility

docker build -t plex-util .

docker run -d -p 8080:8080 -e PLEX_URL=http://192.168.101.103:32400 -e PLEX_TOKEN=c1Lz1ek7jjQWN8gZ8q3G -e FFMPEG_MEDIA=/srv/dev-disk-by-uuid-710d520b-bb51-4d6e-8c51-f4b9d8126a08/WDBlack/Media -v /var/run/docker.sock:/var/run/docker.sock -v /srv/dev-disk-by-uuid-710d520b-bb51-4d6e-8c51-f4b9d8126a08/WDBlack/Docker/Plex-Util/config.json:/etc/config.json --name plex-util plex-util


