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


## Re-Transcoding H265 -> H265

By default, the option to re-transcode H265 -> H265 is enabled. You can turn it off by setting environment variable `H265_TRANSCODE` to False

The other variable `H265_MB_H` defines how many MB/h is your target. If a file is below that target, it will not attempt to re-transcode the file.

It uses the formula `size / duration` instead of the reported bit rate by ffmpeg, as it seems it is often incorrect and not representative of the resulting file size.


## All Environment Variables

| Variable       | Description                                                            | Default |
|----------------|------------------------------------------------------------------------|---------|
| ROOT_PATH      | The path of media to transcode (inside the container)                  | /media  |
| BOT_KEY        | The Telegram bot key                                                   |         |
| CHAT_ID        | The Telegram chat ID to report to                                      |         |
| HOST           | The Host to specify in Telegram messages                               |         |
| CRF            | The Constant Rate Factor quality setting. Lower number, better quality | 16      |
| H265_TRANSCODE | Whether to re-transcode H265 content                                   | True    |
| H265_MB_H      | Minimum MB/h to attempt to re-transcode H265 content                   | 1000    |