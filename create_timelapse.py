import argparse
import datetime
import os
import sys

import ffmpeg
import imageio
from PIL import Image
from pygifsicle import optimize
from vidstab import VidStab

parser = argparse.ArgumentParser(description = "Create a timelapse video/gif from a set of images")
parser.add_argument("-i", "--input-folder", help = "Folder name where the images are located. Default: input", default = "input")
parser.add_argument("-o", "--output-folder", help = "Folder name where the timelapse saved. Default: output", default = "output")
parser.add_argument("-f", "--format", help = "Format of the timelapse (gif/mp4). Default: mp4", default = "mp4")
parser.add_argument("-n", "--name", help = "Name of the timelapse. Default: timelapse", default = "timelapse")
parser.add_argument("-d", "--duration", help = "Duration of the timelapse (s). Default: 60", type = int, default = 60)
parser.add_argument("-s", "--size", help = "Size (MB) of the timelapse video. Available only if format is mp4", type = int, default = None)
parser.add_argument("--fixed-frame-rate", help = "If enabled, every image lasts for equal amount of frames", default = False, dest = "fixed_frame_rate", action = "store_true")
parser.add_argument("--no-stabilize", help = "Don't stabilize the timelapse", default = True, dest = "stabilize", action = "store_false")
args = vars(parser.parse_args())



def main(args):
	input_folder_name = args["input_folder"]
	output_folder_name = args["output_folder"]
	output_file_name = args["name"] + "." + args["format"]
	timelapse_format = args["format"]
	timelapse_duration = args["duration"]
	stabilize = args["stabilize"]
	size = args["size"]
	if size == None:
		size = timelapse_duration
		# size = int(0.3 * timelapse_duration)
	ffr = args["fixed_frame_rate"]
	fps = 20
	
	image_dict = read_input_images(input_folder_name)
	passed_time = get_passed_time(image_dict)
	duration_list = get_duration_list(image_dict, passed_time, timelapse_duration, ffr)
	frame_length_dict = get_frame_length_dict(image_dict, passed_time, timelapse_duration, fps, ffr)

	if timelapse_format == "gif":
		create_gif(image_dict, duration_list, output_folder_name, output_file_name, ffr)
	else:
		create_video(image_dict, output_folder_name, output_file_name, frame_length_dict, fps, ffr, stabilize)
		compress_video(output_folder_name, output_file_name, output_file_name, size * 1000)

	delete_tmp_files(output_folder_name, output_file_name)

def read_input_images(folder_name):
	image_dict = {}
	images = [folder_name + "/" + f for f in os.listdir("./" + folder_name) if os.path.isfile(os.path.join(".", folder_name, f))]
	image_paths = [os.path.abspath(f) for f in images]
	for path in image_paths:
		image_dict[path] = get_taken_timestamp(path)
	sorted_image_dict = dict(sorted(image_dict.items(), key=lambda item: item[1]))
	print("Found " + str(len(sorted_image_dict)) + " images")
	return sorted_image_dict

def print_progress(msg):
	sys.stdout.write('\r')
	sys.stdout.write(msg)
	sys.stdout.flush()

def get_taken_timestamp(path):
	time_format = "%Y:%m:%d %H:%M:%S"
	time_str = Image.open(os.path.abspath(path))._getexif()[36867]
	timestamp = int(datetime.datetime.strptime(time_str, time_format).timestamp())
	return timestamp

def get_passed_time(image_dict):
	max_timestamp = image_dict[list(image_dict)[-1]]
	min_timestamp = image_dict[list(image_dict)[0]]
	return max_timestamp - min_timestamp

def get_frame_length_dict(image_dict, passed_time, timelapse_duration, fps, ffr):
	frame_length_dict = {}
	prev_image = None
	prev_timestamp = None
	ffr_duration = int(fps * timelapse_duration / len(image_dict))
	for image in image_dict:
		timestamp = image_dict[image]
		if ffr:
			frame_duration = ffr_duration
		elif prev_image == None:
			frame_duration = fps
		else:
			frame_duration = int((timestamp - prev_timestamp) * timelapse_duration * fps / passed_time)
		frame_length_dict[image] = frame_duration
		prev_image = image
		prev_timestamp = timestamp
	return frame_length_dict


def get_duration_list(image_dict, passed_time, timelapse_duration, ffr):
	duration_list = []
	prev_image = None
	prev_timestamp = None
	ffr_duration = timelapse_duration / len(image_dict)
	for image in image_dict:
		timestamp = image_dict[image]
		if ffr:
			frame_duration = ffr_duration
		elif prev_image == None:
			frame_duration = 1
		else:
			frame_duration = (timestamp - prev_timestamp) * timelapse_duration / passed_time
		duration_list.append(frame_duration)
		prev_image = image
		prev_timestamp = timestamp
	return duration_list

def create_gif(image_dict, duration_list, output_folder_name, output_file_name, ffr):
	print("Creating gif")
	output_path = os.path.join(".", output_folder_name, output_file_name)
	image_list = list(image_dict)
	if ffr:
		with imageio.get_writer(output_path, mode='I') as writer:
			for filename in image_list:
				image = imageio.imread(filename)
				writer.append_data(image)
	else:
		with imageio.get_writer(output_path, mode='I', duration = duration_list) as writer:
			for filename in image_list:
				image = imageio.imread(filename)
				writer.append_data(image)
	optimize(output_path)
	print("Gif created")

def create_video(image_dict, output_folder_name, output_file_name, frame_length_dict, fps, ffr, stabilize):
	tmp_output_path = os.path.join(".", output_folder_name, "tmp_" + output_file_name)
	output_path = os.path.join(".", output_folder_name, "stable_" + output_file_name)
	image_list = list(image_dict)
	image_count = len(image_dict)
	counter = 0
	with imageio.get_writer(tmp_output_path, fps=fps) as writer:
		for filename in image_list:
			# print_progress("Adding frames to video: " + str(int(100 * counter/len(image_dict))) + "%")
			image = imageio.imread(filename)
			if not ffr:
				for i in range(frame_length_dict[filename]):
					writer.append_data(image)
			counter += 1
			print_progress(str(counter) + "/" + str(image_count) + " Images added to video")
	print()

	if stabilize:
		stabilizer = VidStab()
		stabilizer.stabilize(input_path = tmp_output_path, output_path = output_path)

def compress_video(input_folder_name, input_file_name, output_file_name, target_size):
	# Reference: https://stackoverflow.com/questions/64430805/how-to-compress-video-to-target-size-by-python

	print("Compressing video")
	input_full_path = os.path.join(".", input_folder_name, "stable_" + input_file_name)
	output_full_path = os.path.join(".", input_folder_name, output_file_name)

	probe = ffmpeg.probe(input_full_path)
	# Video duration, in s.
	duration = float(probe['format']['duration'])
	# Target total bitrate, in bps.
	target_total_bitrate = (target_size * 1024 * 8) / (1.073741824 * duration)

	video_bitrate = target_total_bitrate

	i = ffmpeg.input(input_full_path)
	ffmpeg.output(i, os.devnull,
                  **{'c:v': 'libx264', 'b:v': video_bitrate, 'pass': 1, 'f': 'mp4'}
                  ).global_args('-loglevel', 'error').overwrite_output().run()
	ffmpeg.output(i, output_full_path,
                  **{'c:v': 'libx264', 'b:v': video_bitrate, 'pass': 2, 'c:a': 'aac'}
                  ).global_args('-loglevel', 'error').overwrite_output().run()

def delete_tmp_files(output_folder_name, output_file_name):
	if os.path.isfile(os.path.join(".", output_folder_name, "tmp_" + output_file_name)):
		os.remove(os.path.join(".", output_folder_name, "tmp_" + output_file_name))
	if os.path.isfile(os.path.join(".", output_folder_name, "stable_" + output_file_name)):
		os.remove(os.path.join(".", output_folder_name, "stable_" + output_file_name))


main(args)