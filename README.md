# Create a timelapse

This is a simple python project for making a timelapse video from a set of images.

It will read the images from an input folder, adds them to a video, stabilizes the video, and finally compresses the video.

## Installation

1. Clone the project
2. Create a virtual environment
3. Install ffmpeg. [https://ffmpeg.org/download.html]
4. Install Pip packages from the requirements.txt

## Usage

### Basic usage with default options

python3 create_timelapse.py

### Modify input and output directories

python3 create_timelapse.py -i foo -o bar

### Modify duration of the timelapse

python3 create_timelapse.py -d 10

### For other options, see help

python3 create_timelapse.py --help