import os
import random

import pyaudio
import numpy as np
import aubio

import pygame

from threading import Thread

import queue
import time

import argparse

SCREEN_SIZE = (1024, 768)
CHANGE_IMAGE_LIKENESS = 0.3
COLORS = [
#  (229, 244, 227),
   (93, 169, 233),
   (0, 63, 145),
#  (255, 255, 255),
   (109, 50, 109)
]
CIRCLE_SIZE_MIN = 0.1
CIRCLE_SIZE_MAX = 0.5
TOLERANCE = 0.8

WORK_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(WORK_DIR, 'images')

IMAGES = os.listdir(IMAGES_DIR)
IMAGES = list(filter(lambda x: os.path.splitext(x)[1] in ['.jpg', '.png', '.jpeg', '.tiff', '.webp'], IMAGES))
IMAGES_TOTAL = len(IMAGES)

parser = argparse.ArgumentParser()
parser.add_argument("-input", required=False, type=int, help="Audio Input Device")
parser.add_argument("-f", action="store_true", help="Run in Fullscreen Mode")
args = parser.parse_args()

if args.input != 0 and not args.input:
    print("No input device specified. Printing list of input devices now: ")
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        print("Device number (%i): %s" % (i, p.get_device_info_by_index(i).get('name')))
    print("Run this program with -input 1, or the number of the input you'd like to use.")
    exit()

pygame.init()

if args.f:
    screenWidth, screenHeight = SCREEN_SIZE
    screen = pygame.display.set_mode((screenWidth, screenHeight), pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)

else:
    screenWidth, screenHeight = SCREEN_SIZE
    screen = pygame.display.set_mode((screenWidth, screenHeight))

white = (255, 255, 255)
black = (0, 0, 0)

class Circle(object):
    def __init__(self, x, y, color, size):
        self.x = x
        self.y = y
        self.color = color
        self.size = size

    def shrink(self):
        self.size -= 3


circleList = []

# initialise pyaudio
p = pyaudio.PyAudio()

clock = pygame.time.Clock()

# open stream

buffer_size = 4096 # needed to change this to get undistorted audio
pyaudio_format = pyaudio.paFloat32
n_channels = 1
samplerate = 44100
stream = p.open(format=pyaudio_format,
                channels=n_channels,
                rate=samplerate,
                input=True,
                input_device_index=args.input,
                frames_per_buffer=buffer_size)

time.sleep(1)

# setup onset detector
tolerance = TOLERANCE
win_s = 4096 # fft size
hop_s = buffer_size // 2 # hop size
onset = aubio.onset("default", win_s, hop_s, samplerate)

q = queue.Queue()

def draw_it_baby():
    running = True
    current_image = os.path.join(IMAGES_DIR, random.choice(IMAGES))

    while running:
        key = pygame.key.get_pressed()

        if key[pygame.K_q]:
            running = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if not q.empty():
            b = q.get()
            newCircle = Circle(random.randint(0, screenWidth), random.randint(0, screenHeight),
                               random.choice(COLORS), random.randint(int(screenWidth * CIRCLE_SIZE_MIN), int(screenWidth * CIRCLE_SIZE_MAX)))
            circleList.append(newCircle)

            if random.random() < CHANGE_IMAGE_LIKENESS:
                current_image = os.path.join(IMAGES_DIR, random.choice(IMAGES))

        screen.fill(black)

        img = pygame.image.load(current_image)
        img_size = img.get_size()
        # proportions = img_size[0] / img_size[1]
        # if img_size[0] < SCREEN_SIZE[0]:
        img = pygame.transform.scale(img, SCREEN_SIZE)
        screen.blit(img, (0,0))

        surface = pygame.Surface(SCREEN_SIZE)

        for place, circle in enumerate(circleList):
            if circle.size < 1:
                circleList.pop(place)
            else:
                pygame.draw.circle(surface, circle.color, (circle.x, circle.y), circle.size)
            circle.shrink()

        surface.set_alpha(128)
        screen.blit(surface, (0,0))
        pygame.display.flip()
        clock.tick(90)

def get_onsets():
    while True:
        try:
            buffer_size = 2048 # needed to change this to get undistorted audio
            audiobuffer = stream.read(buffer_size, exception_on_overflow=False)
            signal = np.fromstring(audiobuffer, dtype=np.float32)

            if onset(signal):
                q.put(True)


        except KeyboardInterrupt:
            print("*** Ctrl+C pressed, exiting")
            break


t = Thread(target=get_onsets, args=())
t.daemon = True
t.start()

draw_it_baby()
stream.stop_stream()
stream.close()
pygame.display.quit()