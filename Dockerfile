FROM vilsol/ffmpeg-alpine as build

FROM python:alpine3.6

RUN echo "@testing http://dl-cdn.alpinelinux.org/alpine/edge/testing" >> /etc/apk/repositories

RUN apk add --no-cache \
	libtheora \
	libvorbis \
	x264-libs \
	x265 \
	fdk-aac@testing \
	lame \
	opus \
	libvpx

COPY --from=build /root/bin/ffmpeg /bin/ffmpeg
COPY --from=build /root/bin/ffprobe /bin/ffprobe
COPY --from=build /root/bin/ffserver /bin/ffserver
COPY --from=build /root/bin/nasm /bin/nasm
COPY --from=build /root/bin/ndisasm /bin/ndisasm

RUN pip install --no-cache-dir tqdm pexpect telepot

VOLUME /media

COPY transcoder.py /transcoder.py

CMD ["/usr/local/bin/python3", "/transcoder.py"]
