#!/bin/python3

from tqdm import tqdm

import os
import time
import sys
import subprocess
import pexpect


ROOT_PATH = os.getenv('ROOT_PATH', '/media')


def transcode(file, pbar):
	previous_frame = 0

	cmd = 'ffmpeg -y -i "{}" -map 0 -c copy -c:v libx265 -preset ultrafast -x265-params crf=16 -c:a libfdk_aac -strict -2 -b:a 256k "{}.new.mkv"'.format(file, file)
	thread = pexpect.spawn(cmd)
	
	cpl = thread.compile_pattern_list([
		pexpect.EOF,
		"frame= *\d+",
		'(.+)'
	])

	while True:
		i = thread.expect_list(cpl, timeout=None)
		if i == 0:
			print("the sub process exited")
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

			thread.close
		elif i == 2:
			# unknown_line = thread.match.group(0)
			# print("UN", unknown_line)
			pass

def process(file, desc):
	frames = get_frames(file)

	open(file + '.converting', 'a').close()

	try:
		pbar = tqdm(total=frames, leave=False, unit='', desc=desc)
		transcode(file, pbar)
		pbar.close()
	except:
		print(sys.exc_info()[0])
		pass

	os.remove(file + '.converting')

def get_frames(file):
	return int(get_fps(file) * get_duration(file))

def get_fps(file):
	cmd = ['ffprobe', '-v', '0', '-of', 'default=noprint_wrappers=1:nokey=1', '-show_entries', 'stream=r_frame_rate', '-select_streams', '0', file]
	process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
	fps = process.stdout.read().rstrip().decode("utf-8") 
	fps = fps.split("/")
	return int(fps[0]) / int(fps[1])

def get_duration(file):
	cmd = ['ffprobe', '-v', '0', '-of', 'default=noprint_wrappers=1:nokey=1', '-show_entries', 'format=duration', file]
	process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
	return int(round(float(process.stdout.read().rstrip().decode("utf-8"))))

def has_accessors(file):
	process = subprocess.Popen('lsof', stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

	for line in process.stdout:
		if file in line.rstrip().decode("utf-8"):
			return True

	return False

def is_transcodable(file):
	if file.endswith("partial~"):
		return False

	if os.path.isfile(file + ".converting"):
		return False

	if has_accessors(file):
		return False

	try:
		cmd = ['ffprobe', '-v', '0', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name', '-of', 'default=nokey=1:noprint_wrappers=1', file]
		process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
		codec = process.stdout.read().rstrip()
		if codec == b'h264':
			return True
	except:
		print(sys.exc_info()[0])
		pass

	return False

def search(path, name, depth=0, prefix='', last=True):
	desc = prefix

	if last:
		desc += '└─'
	else:
		desc += '├─'

	if depth > 0:
		print(desc, end='')

	if os.path.isdir(path):
		print(name)

		files = os.listdir(path)
		length = len(files)

		for i in range(length):
			if not last:
				search(path + '/' + files[i], files[i], depth + 1, prefix + '| ', i + 1 == length)
			else:
				search(path + '/' + files[i], files[i], depth + 1, prefix + '  ', i + 1 == length)
	else:
		if is_transcodable(path):
			process(path, desc + name)
		
		print(name)

	pass

def scan():
	search(ROOT_PATH, ROOT_PATH)

scan()