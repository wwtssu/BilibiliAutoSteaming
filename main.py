# -*- coding: utf-8 -*-
from PIL import Image
import threading
import time
import os
import numpy as np 
import io
import datetime
import subprocess
import json
import sys
import random
from queue import Queue

#------ define
vcodec = 'h264_videotoolbox'
#vcodec = 'h264_qsv'
#acodec = 'copy'
acodec = 'aac'
bv = '3000k'
ba = '640k'
resolution = (1280, 720)
aw_string = 'f32le'
aw = 32
ar = 96 * 1000
ac = 2
fps = 60

video_media = [
    '.flv',
    '.mp4',
    '.webm'
]

audio_media = [
    '.aac',
    '.mp3'
]

images_media = [
    '.jpg',
    '.jpeg',
    '.png'
]

#----- end defile

video_send_pipe_path = 'video_send.pipe'
audio_send_pipe_path = 'audio_send.pipe'

video_read_pipe_path = 'video_read.pipe'
audio_read_pipe_path = 'audio_read.pipe'

video_queue=Queue()
audio_queue=Queue()
currentVideo = np.array(Image.new('RGB', resolution, 'black'))
new_start = False

if os.path.exists(video_send_pipe_path):
    os.remove(video_send_pipe_path)
os.mkfifo(video_send_pipe_path)

if os.path.exists(audio_send_pipe_path):
    os.remove(audio_send_pipe_path)
os.mkfifo(audio_send_pipe_path)

if os.path.exists(video_read_pipe_path):
    os.remove(video_read_pipe_path)
os.mkfifo(video_read_pipe_path)

if os.path.exists(audio_read_pipe_path):
    os.remove(audio_read_pipe_path)
os.mkfifo(audio_read_pipe_path)

#------ get work root path
root_dir= os.path.dirname(sys.argv[0])
if root_dir == '':
    root_dir = os.path.abspath('.')
else:
    root_dir = os.path.abspath(root_dir)

#------ get rtmp url

rtmp_url = sys.argv[1]

def get_a_images():
    img_path = os.path.join(root_dir,"images")
    imgs = os.listdir(img_path)
    index = random.randint(0,len(imgs)-1)
    img_file = imgs[index]
    return os.path.join(img_path,img_file)

def get_a_media():
    media_path = os.path.join(root_dir,"media")
    media = os.listdir(media_path)
    index = random.randint(0,len(media)-1)
    media_file = media[index]
    return os.path.join(media_path,media_file)
    
#------

output_command = [
    'ffmpeg',
    #'-loglevel', 'quiet',
    '-y', '-an', '-re',
    '-f', 'rawvideo',
    '-c:v','rawvideo',
    '-pix_fmt', 'rgb24',
    '-s', str(resolution[0]) + 'x' + str(resolution[1]),
    '-r', str(fps),
    '-i', video_send_pipe_path,
    '-f', aw_string,
    '-ar', str(ar),
    '-ac', str(ac),
    '-i', audio_send_pipe_path,
    '-c:v', vcodec,
    '-b:v', bv,
    '-c:a', acodec,
	'-b:a', ba,
    '-f', 'flv',
    rtmp_url
]
subprocess.Popen(output_command, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

video_output_pipe = os.open(video_send_pipe_path, os.O_WRONLY)
def video_send_loop():
    global currentVideo
    while True:
        if not video_queue.empty():
            currentVideo = video_queue.get()
        os.write(video_output_pipe, currentVideo.tobytes())

video_send_thread = threading.Thread(target=video_send_loop,args=())
video_send_thread.start()

audio_output_pipe = os.open(audio_send_pipe_path, os.O_WRONLY)
def audio_send_loop():
    global new_start
    while True:
        if new_start:
            if audio_queue.qsize() < 20:
                os.write(audio_output_pipe, bytes([1 for i in range(0,1000)]))
            else:
                new_start = False
        # elif audio_queue.qsize() > 10:
        #     for i in range(audio_queue.qsize() - 5):
        #         audio_queue.get()
        elif not audio_queue.empty():
            data = audio_queue.get()
            os.write(audio_output_pipe, data)
            if len(data) != int(ar/10):
                os.write(audio_output_pipe, bytes([1 for i in range(0,int(ar/10) - len(data))]))
        else:
            os.write(audio_output_pipe, bytes([1 for i in range(0,int(ar/10))]))
audio_send_thread = threading.Thread(target=audio_send_loop,args=())
audio_send_thread.start()

def read_video(file):
    global new_start
    read_command = [
        'ffmpeg',
        '-loglevel', 'quiet',
        '-re', '-y',
        '-i', file,
        '-r', str(fps),
        '-pixel_format', 'rgb24',
        '-s', str(resolution[0]) + 'x' + str(resolution[1]),
        '-f', 'rawvideo',
        video_read_pipe_path,
        '-f', aw_string,
        '-ar', str(ar),
        '-ac', str(ac),
        audio_read_pipe_path,
    ]
    subprocess.Popen(read_command, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    def video_read_loop():
        video_input_pipe = open(video_read_pipe_path, 'rb')
        while True:
            read = video_input_pipe.read(resolution[0] * resolution[1] * 3)
            if len(read) == 0:
                video_input_pipe.close()
                break
            im = Image.frombuffer('L', resolution, read)
            im = im.convert('RGB')
            video_queue.put(np.array(im))
    video_read_thread = threading.Thread(target=video_read_loop, args=())
    video_read_thread.start()

    
    def audio_read_loop():
        audio_input_pipe = open(audio_read_pipe_path, 'rb')
        while True:
            read = audio_input_pipe.read(int(ar/10))
            if len(read) == 0:
                audio_input_pipe.close()
                break
            audio_queue.put(read)
    audio_read_thread = threading.Thread(target=audio_read_loop, args=())
    new_start = True
    audio_queue.queue.clear()
    audio_read_thread.start()
    audio_read_thread.join()

def read_audio(file):
    global new_start
    read_command = ['ffmpeg',
        '-loglevel', 'quiet',
        '-re', '-y',
        '-i', file,
        '-f', aw_string,
        '-ar', str(ar),
        '-ac', str(ac),
        audio_read_pipe_path,
        ]
    subprocess.Popen(read_command, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    def audio_read_loop():
        audio_input_pipe = open(audio_read_pipe_path, 'rb')
        while True:
            read = audio_input_pipe.read(10000)
            if len(read) == 0:
                audio_input_pipe.close()
                break
            audio_queue.put(read)
    audio_read_thread = threading.Thread(target=audio_read_loop, args=())
    new_start = True
    audio_queue.queue.clear()
    audio_read_thread.start()
    audio_read_thread.join()

while True:
    try:
        media_file = get_a_media()
        print(media_file)
        if os.path.splitext(media_file)[1].lower() in video_media:
            read_video(media_file)
        elif os.path.splitext(media_file)[1].lower() in audio_media:
            img_file = get_a_images()
            while not os.path.splitext(img_file)[1].lower() in images_media:
                img_file = get_a_images()
            im = Image.open(img_file)
            im = im.resize(resolution)
            im = im.convert('RGB')
            currentVideo = np.array(im)
            read_audio(media_file)
        else:
            continue
    except Exception as e:
        print(e)
        continue
