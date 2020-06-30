# -*- coding: utf-8 -*-
import sys
import os
import random
from pydub.utils import mediainfo

#------ define
#vcodec = 'h264_videotoolbox'
vcodec = 'libx264'
#acodec = 'copy'
acodec = 'aac'

args = '-preset veryfast'

width = 1920
height = 1080

bv = '3000k'
ba = '320k'

video_media = [
    '.flv',
    '.mp4'
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

def ass_list():
    ass_path = os.path.join(root_dir,"ass")
    asss = os.listdir(ass_path)
    ret = ''
    for ass in asss:
        if os.path.splitext(ass)[1] == '.ass':
            ret = ret + "ass=\'{}\',".format(os.path.join(ass_path,ass))
    if len(ret) == 0:
        return None
    else:
        return ret[0:-1]
#------
while True:
    try:
        command = 'ffmpeg '
        media_file = get_a_media()
        ass_str = ass_list()
        if os.path.splitext(media_file)[1].lower() in video_media:
            command = command + "-re -i \"{}\" ".format(media_file)
            command = command + "-filter_complex \"[0:v]scale={w}:{h}".format(w = width,h = height)
            if ass_str != None:
                command = command + "[v1];[v1]{}".format(ass_str)
            command = command + "\" -vcodec {vcodec} -acodec {acodec} -b:v {bv} -b:a {ba} {args} -f flv \"{output}\"".format(vcodec = vcodec, acodec = acodec, bv = bv, ba = ba, args = args, output = rtmp_url)
            #print(command)
        elif os.path.splitext(media_file)[1].lower() in audio_media:
            img_file = get_a_images()
            if not os.path.splitext(img_file)[1].lower() in images_media:
                continue
            audio = mediainfo(media_file)
            to = audio['duration']
            command = command + "-re -i \"{}\" ".format(media_file)
            command = command + "-f lavfi -i color=c=0x000000:s={w}x{h}:r=30 ".format(w = width, h = height)
            command = command + "-i \"{}\" ".format(img_file)
            command = command + "-filter_complex \"[2:v]scale={w}:{h}[v1];[1:v][v1]overlay=0:0".format(w = width, h = height)
            if ass_str != None:
                command = command + "[v2];[v2]{}".format(ass_str)
            command = command + "\" -ss 0 -to {to} -vcodec {vcodec} -acodec {acodec} -b:v {bv} -b:a {ba} {args} -f flv \"{output}\"".format(to = to, vcodec = vcodec, acodec = acodec, bv = bv, ba = ba, args = args, output = rtmp_url)
        else:
            continue
        ret = os.system(command)
        if ret == 65280:
            exit(0)
    except Exception:
        continue