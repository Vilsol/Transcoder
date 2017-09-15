FROM alpine as build

RUN echo "@testing http://dl-cdn.alpinelinux.org/alpine/edge/testing" >> /etc/apk/repositories

RUN cat /etc/apk/repositories

RUN apk add --no-cache \
	autoconf \
	automake \
	g++ \
	make \
	gcc \
	libc-dev \
	libtheora-dev \
	libtool \
	libvorbis-dev \
	pkgconfig \
	texinfo \
	wget \
	zlib-dev \
	yasm \
	x264-dev \
	x265-dev \
	fdk-aac-dev@testing \
	lame-dev \
	opus-dev \
	libvpx-dev \
	coreutils

RUN mkdir ~/ffmpeg_sources

RUN cd ~/ffmpeg_sources \
	&& wget http://www.nasm.us/pub/nasm/releasebuilds/2.13.01/nasm-2.13.01.tar.bz2 \
	&& tar xjvf nasm-2.13.01.tar.bz2 \
	&& cd nasm-2.13.01 \
	&& ./autogen.sh \
	&& PATH="$HOME/bin:$PATH" ./configure --prefix="$HOME/ffmpeg_build" --bindir="$HOME/bin" \
	&& PATH="$HOME/bin:$PATH" make -j8 \
	&& make install

RUN cd ~/ffmpeg_sources \
	&& wget http://ffmpeg.org/releases/ffmpeg-snapshot.tar.bz2 \
	&& tar xjvf ffmpeg-snapshot.tar.bz2 \
	&& cd ffmpeg \
	&& PATH="$HOME/bin:$PATH" PKG_CONFIG_PATH="$HOME/ffmpeg_build/lib/pkgconfig" ./configure \
		--prefix="$HOME/ffmpeg_build" \
		--pkg-config-flags="--static" \
		--extra-cflags="-I$HOME/ffmpeg_build/include" \
		--extra-ldflags="-L$HOME/ffmpeg_build/lib" \
		--bindir="$HOME/bin" \
		--enable-gpl \
		--enable-libfdk-aac \
		--enable-libmp3lame \
		--enable-libopus \
		--enable-libtheora \
		--enable-libvorbis \
		--enable-libvpx \
		--enable-libx264 \
		--enable-libx265 \
		--enable-nonfree \
	&& PATH="$HOME/bin:$PATH" make -j8 \
	&& make install \
	&& hash -r

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

RUN pip install --no-cache-dir tqdm pexpect python-telegram-bot

COPY transcoder.py /transcoder.py

CMD ["/usr/local/bin/python3", "/transcoder.py"]