#!/bin/python3

from tqdm import tqdm

import os
import sys
import subprocess
import pexpect
import math
import telegram
import signal


ROOT_PATH = os.getenv('ROOT_PATH', '/media')
BOT_KEY = os.getenv('BOT_KEY', '')
CHAT_ID = os.getenv('CHAT_ID', '')
HOST = os.getenv('HOST', '')
CRF = os.getenv('CRF', '16')
H265_TRANSCODE = os.getenv('H265_TRANSCODE', 'true')
H265_MB_H = os.getenv('H265_MB_H', '1000')


stopping = False


def transcode(file, pbar):
	previous_frame = 0

	cmd = 'ffmpeg -y -i "{}" -map 0 -c copy -c:v libx265 -preset ultrafast -x265-params crf={} -c:a libfdk_aac -strict -2 -b:a 256k "{}.new.mkv"'.format(file, CRF, file)
	thread = pexpect.spawn(cmd)

	cpl = thread.compile_pattern_list([
		pexpect.EOF,
		"frame= *\d+",
		'(.+)'
	])

	while True:
		if stopping:
			thread.kill(9)
			break

		i = thread.expect_list(cpl, timeout=None)
		if i == 0:
			break
		elif i == 1:
			line = thread.match.group(0).decode("utf-8")

			try:
				frame_number = int(line.split('=')[-1])
				frame_count = frame_number - previous_frame
				previous_frame = frame_number
				pbar.update(frame_count)
			except ValueError:
				print(line)
		elif i == 2:
			# unknown_line = thread.match.group(0)
			# print("UN", unknown_line)
			pass

	if not stopping:
		original = os.path.getsize(file)
		converted = os.path.getsize(file + '.new.mkv')

		directory = os.path.dirname(file)
		with open(directory + "/." + os.path.basename(file + ".processed"), 'w') as f:
			if original < converted:
				f.write(str(original))
				os.remove(file + '.new.mkv')
			else:
				f.write(str(converted))
				os.remove(file)
				os.rename(file + '.new.mkv', file)

		return original, converted

	os.remove(file + '.new.mkv')

	return -1, -1


def process(file, desc, data):
	frames = get_frames(data)

	open(file + '.converting', 'a').close()

	result = (0, 0)

	try:
		pbar = tqdm(total=frames, leave=False, unit='', desc=desc)
		result = transcode(file, pbar)
		pbar.close()
	except:
		print(sys.exc_info()[0])
		pass

	os.remove(file + '.converting')

	return result


def get_frames(data):
	frames = 0

	for i in data['stream']:
		temp = data['stream'][i]['nb_frames']
		if temp != 'N/A':
			if int(temp) < frames:
				frames = int(temp)

	if frames > 0:
		return frames

	return int(get_fps(data) * get_duration(data))


def get_fps(data):
	fps = get_key_from_stream(data, 'r_frame_rate')

	if fps == 'N/A':
		fps = get_key_from_stream(data, 'avg_frame_rate')

	fps = fps.split("/")
	return int(fps[0]) / int(fps[1])


def get_duration(data):
	if data['format']['duration'] == 'N/A':
		return 0

	return int(round(float(data['format']['duration'])))


def get_key_from_stream(data, key):
	for i in data['stream']:
		if data['stream'][i][key] != 'N/A' and data['stream'][i][key] != '0/0':
			return data['stream'][i][key]


def get_data(file):
	cmd = ['ffprobe', '-v', '0', '-show_format', '-show_streams', file]
	process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

	data = {'stream': {}}

	stream = -1
	tag = None
	for line in process.stdout:
		line = line.rstrip().decode("utf-8")
		if line.startswith('['):
			if tag is None:
				tag = line[1:-1].lower()
				if tag == 'stream':
					stream = stream + 1
					data[tag][stream] = {}
				else:
					data[tag] = {}
			else:
				tag = None
		else:
			kv = line.split("=")
			if tag == 'stream':
				data[tag][stream][kv[0]] = kv[1]
			else:
				data[tag][kv[0]] = kv[1]

	return data


def has_accessors(file):
	process = subprocess.Popen('lsof', stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

	for line in process.stdout:
		if file in line.rstrip().decode("utf-8"):
			return True

	return False


def is_transcodable(file, data):
	if len(data['stream']) == 0:
		return False

	found_h264 = False
	found_h265 = False
	for i in data['stream']:
		if data['stream'][i]['codec_name'] == 'h264':
			found_h264 = True
			break
		elif data['stream'][i]['codec_name'] == 'h265' or data['stream'][i]['codec_name'] == 'hevc':
			found_h265 = True
			break

	transcode_h265 = False

	if found_h265 and H265_MB_H != '':
		size = os.path.getsize(file)
		duration = get_duration(data)
		if duration > 0:
			mb_h = ((size / duration) / 1000000) * 3600
			if mb_h > int(H265_MB_H):
				transcode_h265 = True

	if not found_h264 and not transcode_h265:
		return False

	if file.endswith("partial~"):
		return False

	if os.path.isfile(file + ".converting"):
		return False

	directory = os.path.dirname(file)

	if os.path.isfile(file + ".processed"):
		os.rename(file + ".processed", directory + "/." + os.path.basename(file) + ".processed")

	if os.path.isfile(directory + "/." + os.path.basename(file) + ".processed"):
		return False

	if os.path.isfile(directory + "/.transcodeignore"):
		return False

	if has_accessors(file):
		return False

	return True


def convert_size(size_bytes):
	if size_bytes == 0:
		return "0B"

	size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
	i = int(math.floor(math.log(size_bytes, 1024)))
	p = math.pow(1024, i)
	s = round(size_bytes / p, 2)

	return "%s %s" % (s, size_name[i])


def str2bool(v):
	return v.lower() in ("yes", "true", "t", "1")


def search(path, name, depth=0, prefix='', last=True):
	if stopping:
		return

	desc = prefix + '+-'

	if depth > 0:
		print(desc, end='')

	if os.path.isdir(path):
		files = os.listdir(path)
		length = len(files)

		if ".transcodeignore" in files:
			print(name + ' [ignored]')
		else:
			print(name)

			for i in range(length):
				if not last:
					search(path + '/' + files[i], files[i], depth + 1, prefix + '| ', i + 1 == length)
				else:
					search(path + '/' + files[i], files[i], depth + 1, prefix + '  ', i + 1 == length)
	else:
		try:
			data = get_data(path)
		except:
			data = None
			print(sys.exc_info()[0])

		if data is not None:
			if is_transcodable(path, data):
				print(name + '... ', end='')

				result = process(path, desc + name, data)

				if result[0] > 0:
					diff = round((result[1] / result[0]) * 100, 2)

					oldsize = convert_size(result[0])
					newsize = convert_size(result[1])

					if result[1] > result[0]:
						print('{} -> {} ({}%) (kept old)'.format(oldsize, newsize, diff))
						send_message('*{}*\n*Size:* {} --> {} ({}%)\n*Status:* Kept old'.format(name, oldsize, newsize, diff))
					else:
						print('{} -> {} ({}%)'.format(oldsize, newsize, diff))
						send_message('*{}*\n*Size:* {} --> {} ({}%)\n*Status:* Replaced with new'.format(name, oldsize, newsize, diff))
				elif result[0] != -1:
					print('failed')

			else:
				print(name)


def send_message(message):
	if BOT_KEY != '' and CHAT_ID != '':
		if HOST != '':
			message += '\n*Host:* {}'.format(HOST)

		bot = telegram.Bot(token=BOT_KEY)
		bot.send_message(
			chat_id=CHAT_ID,
			text=message,
			parse_mode=telegram.ParseMode.MARKDOWN
		)


def sigterm_handler(_signo, _stack_frame):
	global stopping
	stopping = True


def scan():
	signal.signal(signal.SIGTERM, sigterm_handler)

	send_message("*Transcoder Started*")
	search(ROOT_PATH, ROOT_PATH)
	send_message("*Transcoder Stopped*")

	print()
	print("Stopped")


if __name__ == "__main__":
	scan()
