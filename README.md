# Transcoder

Docker container to transcode videos in mounted volume to H265

## To run

1. Change the volume to point at your root media folder
2. `docker-compose up -d`

## To view live transcoding

`docker logs transcoder_transcoder_1 && docker attach --no-stdin transcoder_transcoder_1`

(CTRL-C is safe to exit with)

## Telegram notifications

1. Create a .env file
2. Set `BOT_KEY` and `CHAT_ID` variables
3. Recreate the container

## Ignoring files

You can ignore files using `.transcodeignore`, which will make it not transcode any files in that directory or subdirectories.