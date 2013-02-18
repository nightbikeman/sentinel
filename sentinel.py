#!/usr/bin/python

# SENTINEL
# A USB rocket launcher face-tracking solution
# For Linux and Windows
#
# Hardware requirements:
# - Dream Cheeky brand USB rocket launcher (tested with Thunder model, should also work with Storm)
# - small webcam attached to USB rocket launcher, in /dev/video0
#
# Software requirements (Linux):
# - Python 2.7, 32-bit
# - libusb (in Ubuntu/Debian, apt-get install libusb-dev)
# - PyUSB 1.0 (https://github.com/walac/pyusb)
# - NumPy (in Ubuntu/Debian, apt-get install python-numpy)
# - OpenCV Python bindings (in Ubuntu/Debian, apt-get install python-opencv)
# - PIL (in Ubuntu/Debian, apt-get install python-imaging)
# - streamer (in Ubuntu/Debian, apt-get install streamer)
#
# Software requirements (Windows):
# - Python 2.7, 32-bit
# - libusb (http://sourceforge.net/projects/libusb-win32/files/)
#     - After installing, plug in USB rocket launcher, launch <libusb path>\bin\inf-wizard.exe,
#       and create and run an INF driver file for the USB rocket launcher using the wizard
# - PyUSB 1.0 (https://github.com/walac/pyusb)
# - NumPy (http://www.lfd.uci.edu/~gohlke/pythonlibs/#numpy)
# - OpenCV Python bindings (http://sourceforge.net/projects/opencvlibrary/files/opencv-win/2.3.1/OpenCV-2.3.1-win-superpack.exe/download)
#     - After installing, copy the contents of <opencv path>\build\python\2.7 (it should contain cv.py and cv2.pyd)
#       to c:\Python27\Lib
# - PIL (http://www.lfd.uci.edu/~gohlke/pythonlibs/#pil)

import os
import sys
import time
import usb.core
import cv   #legacy OpenCV functions
import cv2
import subprocess
from PIL import Image
from optparse import OptionParser

# globals
FNULL = open(os.devnull, 'w')

class LauncherDriver():
   # Low level launcher driver commands
   # this code mostly taken from https://github.com/nmilford/stormLauncher
   # with bits from https://github.com/codedance/Retaliation
   def __init__(self):
      self.dev = usb.core.find(idVendor=0x2123, idProduct=0x1010)
      if self.dev is None:
         raise ValueError('Launcher not found.')
      if os.name == 'posix' and self.dev.is_kernel_driver_active(0) is True:
         self.dev.detach_kernel_driver(0)
      self.dev.set_configuration()

   def turretUp(self):
      self.dev.ctrl_transfer(0x21,0x09,0,0,[0x02,0x02,0x00,0x00,0x00,0x00,0x00,0x00])

   def turretDown(self):
      self.dev.ctrl_transfer(0x21,0x09,0,0,[0x02,0x01,0x00,0x00,0x00,0x00,0x00,0x00])

   def turretLeft(self):
      self.dev.ctrl_transfer(0x21,0x09,0,0,[0x02,0x04,0x00,0x00,0x00,0x00,0x00,0x00])

   def turretRight(self):
      self.dev.ctrl_transfer(0x21,0x09,0,0,[0x02,0x08,0x00,0x00,0x00,0x00,0x00,0x00])

   def turretStop(self):
      self.dev.ctrl_transfer(0x21,0x09,0,0,[0x02,0x20,0x00,0x00,0x00,0x00,0x00,0x00])

   def turretFire(self):
      self.dev.ctrl_transfer(0x21,0x09,0,0,[0x02,0x10,0x00,0x00,0x00,0x00,0x00,0x00])

   def ledOn(self):
      self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x03, 0x01, 0x00,0x00,0x00,0x00,0x00,0x00])

   def ledOff(self):
      self.dev.ctrl_transfer(0x21, 0x09, 0, 0, [0x03, 0x00, 0x00,0x00,0x00,0x00,0x00,0x00])

class Turret():
   def __init__(self):
      self.launcher = LauncherDriver()
      self.center()
      self.launcher.ledOff()

   # turn off turret properly
   def dispose(self):
      self.launcher.turretStop()
      turret.launcher.ledOff()

   # roughly centers the turret
   def center(self):
      self.launcher.turretLeft()
      time.sleep(4)
      self.launcher.turretRight()
      time.sleep(2)
      self.launcher.turretStop()

      self.launcher.turretUp()
      time.sleep(1)
      self.launcher.turretDown()
      time.sleep(0.25)
      self.launcher.turretStop()

   # adjusts the turret's position (units are fairly arbitary but work ok)
   def adjust(self, rightDist, downDist):
      rightSeconds = rightDist * 0.64
      downSeconds = downDist * 0.48

      if rightSeconds > 0:
         self.launcher.turretRight()
         time.sleep(rightSeconds)
         self.launcher.turretStop()
      elif rightSeconds < 0:
         self.launcher.turretLeft()
         time.sleep(- rightSeconds)
         self.launcher.turretStop()

      if downSeconds > 0:
         self.launcher.turretDown()
         time.sleep(downSeconds)
         self.launcher.turretStop()
      elif downSeconds < 0:
         self.launcher.turretUp()
         time.sleep(- downSeconds)
         self.launcher.turretStop()
      time.sleep(.2)

class Camera():
   def __init__(self, cam_number):
      self.buffer_size = 2
      if os.name == 'posix':
         self.cam_number = cam_number
      else:
         self.cam_number = str(int(cam_number) +1) #camera numbers start at 1 in Windows
      self.current_image_viewer = None #image viewer not yet launched
      self.FNULL = open(os.devnull, 'w')

      self.webcam=cv2.VideoCapture(int(cam_number)) #open a channel to our camera
      if(not self.webcam.isOpened()): #return error if unable to connect to hardware
         raise ValueError('Error connecting to specified camera')

      self.clearBuffer(self.buffer_size)

   def clearBuffer(self, bufferSize):
      #grabs several images from buffer to attempt to clear out old images
      for i in range(bufferSize):
         retval, most_recent_frame = self.webcam.retrieve(channel=0)
         if (not retval):
            raise ValueError('no more images in buffer, mate')
   def dispose(self):
      self.webcam.release()
      #if os.name == 'posix':
      #   os.system("killall display")

   def capture(self, img_file):
      #just use OpenCV to grab camera frames independent of OS
      retval= self.webcam.grab()
      if (not retval):
         raise ValueError('frame grab failed')
      self.clearBuffer(self.buffer_size)
      retval, most_recent_frame = self.webcam.retrieve(channel=0)

      #retval, img = self.webcam.read()
      if (retval):
         self.current_frame = most_recent_frame
      else:
         raise ValueError('frame capture failed')
      # cv2.imwrite(img_file, self.current_frame)

      #if os.name == 'posix':
         #os.system("streamer -c /dev/video" + self.cam_number + " -b 16 -o " + img_file)
         # generates 320x240 greyscale jpeg
      #else:
         #subprocess.call("CommandCam /delay 100 /devnum " + self.cam_number, stdout=self.FNULL)
         # generates 640x480 color bitmap

   def face_detect(self, img_file, haar_file, out_file):
      def drawReticule(img, x, y, width, height, color, style = "corners"):
         w=width
         h=height
         if style=="corners":
            cv2.line(img, (x,y), (x+w/3,y), color, 2)
            cv2.line(img, (x+2*w/3,y), (x+w,y), color, 2)
            cv2.line(img, (x+w,y), (x+w,y+h/3), color, 2)
            cv2.line(img, (x+w,y+2*h/3), (x+w,y+h), color, 2)
            cv2.line(img, (x,y), (x,y+h/3), color, 2)
            cv2.line(img, (x,y+2*h/3), (x,y+h), color, 2)
            cv2.line(img, (x,y+h), (x+w/3,y+h), color, 2)
            cv2.line(img, (x+2*w/3,y+h), (x+w,y+h), color, 2)
         else:
            cv2.rectangle(img, (x,y), (x+w,y+h), color)

      hc = cv.Load(haar_file)
      #img = cv.LoadImage(img_file)
      img = self.current_frame
      #img = cv2.imread(img_file)
      img_w, img_h = (320, 240)
      #img_w, img_h = Image.open(img_file).size
      img = cv2.resize(img, (img_w, img_h))
      #faces = cv.HaarDetectObjects(img, hc, cv.CreateMemStorage())
      face_filter = cv2.CascadeClassifier(haar_file)
      faces = list(face_filter.detectMultiScale(img, minNeighbors=4))
      print faces
      faces.sort(key=lambda face:face[2]*face[3]) # sort by size of face (we use the last face for computing xAdj, yAdj)

      xAdj, yAdj = 0, 0
      if len(faces) > 0:
         face_detected = 1
         for (x,y,w,h) in faces[:-1]:   #draw a rectangle around all faces except last face
            drawReticule(img,x,y,w,h,(0 , 0, 60),"box")

         # get last face
         (x,y,w,h) = faces[-1]
         drawReticule(img,x,y,w,h,(0 , 0, 170),"corners")

         xAdj =  ((x + w/2) - img_w/2) / float(img_w)
         yAdj = ((y + h/2) - img_h/2) / float(img_h)

      else:
         face_detected = 0
      cv2.imwrite(out_file, img)

      return xAdj, yAdj, face_detected



   def display(self, img_file):
      #display the image with faces indicated by a rectangle
      if os.name == 'posix':
         os.system("killall display")
         img = Image.open(img_file)
         img.show()
      else:
         if not self.current_image_viewer:
            ImageViewer = 'rundll32 "C:\Program Files\Windows Photo Viewer\PhotoViewer.dll" ImageView_Fullscreen'
            self.current_image_viewer = subprocess.Popen('%s %s\%s' % (ImageViewer, os.getcwd(),processed_img_file))

if __name__ == '__main__':
   if os.name == 'posix' and not os.geteuid() == 0:
       sys.exit("Script must be run as root.")

   parser = OptionParser()
   parser.add_option("-c", "--camera", dest="camera", default='0',
                     help="specify the camera to use.  By default we will use camera 0.", metavar="PATH")
   parser.add_option("-r", "--reset", action="store_true", dest="reset_only", default=False,
                     help="reset the camera and exit")
   parser.add_option("-a", "--arm", action="store_true", dest="armed", default=False,
                     help="enable the rocket launcher to fire")
   parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                     help="output timing information")
   opts, args = parser.parse_args()
   print opts

   turret = Turret()
   camera = Camera(opts.camera)

   raw_img_file = 'capture.jpeg' if os.name == 'posix' else 'image.bmp' #specify file names
   processed_img_file = 'capture_faces.jpg'

   if not opts.reset_only:
      while True:
         try:
            start_time = time.time()

            camera.capture(raw_img_file)
            capture_time = time.time()

            xAdj, yAdj, face_detected = camera.face_detect(raw_img_file, "haarcascade_frontalface_default.xml", processed_img_file)
            detection_time = time.time()
            camera.display(processed_img_file)

            print "adjusting camera: " + str([xAdj, yAdj])
            turret.adjust(xAdj, yAdj)
            movement_time = time.time()

            if opts.verbose:
               print "capture time: " + str(capture_time-start_time)
               print "detection time: " + str(detection_time-capture_time)
               print "movement time: " + str(movement_time-detection_time)

            #FIRE!!!
            if (face_detected and abs(xAdj)<.05 and abs(yAdj)<.05):
               turret.launcher.ledOn()
               if opts.armed:    #fire missiles if camera armed
                  turret.launcher.turretFire()
            else:
               turret.launcher.ledOff()
         except KeyboardInterrupt:
            turret.dispose()
            camera.dispose()
            break
