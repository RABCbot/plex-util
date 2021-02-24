docker build -t plex-util .</br>
docker run -d -p 8080:8080 -e PLEX_URL=http://<docker-ip>:32400 -e PLEX_TOKEN=<your-plex-token> -v /var/run/docker.sock:/var/run/docker.sock --name plex-util plex-util
