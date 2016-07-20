'''

ofxPublishScreen subscriber backend (WIP)

# requirements
# ofxPublishScreen publisher

'''

import cv2
import numpy as np
from time import time,sleep
import datetime
import zmq

#logging
import logging
logger = logging.getLogger(__name__)


class CameraCaptureError(Exception):
    """General Exception for this module"""
    def __init__(self, arg):
        super(FileCaptureError, self).__init__()
        self.arg = arg

class Frame(object):
    """docstring of Frame"""
    def __init__(self, timestamp,img,index):
        self.timestamp = timestamp
        self.img = img
        self.bgr = img
        self.height,self.width,_ = img.shape
        self._gray = None
        self.index = index
        #indicate that the frame does not have a native yuv or jpeg buffer
        self.yuv_buffer = None
        self.jpeg_buffer = None

    @property
    def gray(self):
        if self._gray is None:
            self._gray = cv2.cvtColor(self.img,cv2.COLOR_BGR2GRAY)
        return self._gray
    @gray.setter
    def gray(self, value):
        raise Exception('Read only.')

class ofxPublishScreen_Capture(object):
    """docstring for ofxPublishScreen Capture"""
    def __init__(self, ip, port):
        super(ofxPublishScreen_Capture, self).__init__()
        self.fps = 30
        self.presentation_time = time()
        self.make_img((320,240))
        self.frame_count = 0
        self.controls = []

        # Prepare our context and publisher
        self.zmq_context    = zmq.Context()
        self.subscriber = self.zmq_context.socket(zmq.SUB)
        addr_str = "tcp://%s:%d" % (ip, port)
        #addr_str = "tcp://192.168.20.204:20000"
        logger.info(addr_str)
        self.subscriber.connect(addr_str)
        #self.subscriber.connect("tcp://192.168.20.204:20000")
        self.subscriber.setsockopt(zmq.SUBSCRIBE,'')

# # We never get here but clean up anyhow
# subscriber.close()
# context.term()

    def make_img(self,size):
        c_w ,c_h = max(1,size[0]/30),max(1,size[1]/30)
        coarse = np.random.randint(0,200,size=(c_h,c_w,3)).astype(np.uint8)
        # coarse[:,:,1] /=5
        # coarse[:,:,2] *=0
        # coarse[:,:,1] /=30
        # self.img = np.ones((size[1],size[0],3),dtype=np.uint8)
        self.img = cv2.resize(coarse,size,interpolation=cv2.INTER_LANCZOS4)

    def get_frame(self):
        now =  time()
        spent = now - self.presentation_time
        wait = max(0,1./self.fps - spent)
        sleep(wait)
        self.presentation_time = time()
        frame_count = self.frame_count
        self.frame_count +=1

        jpeg_buffer = self.subscriber.recv()
        nparr = np.fromstring(jpeg_buffer, np.uint8)
        self.img = cv2.imdecode(nparr, cv2.CV_LOAD_IMAGE_COLOR)
        return Frame(now,self.img.copy(),frame_count)

        #cv2.imshow('image', img)
        #cv2.waitKey(1)

    def get_frame_robust(self):
        return self.get_frame()

    @property
    def frame_size(self):
        #print(self.name ,(self.img.shape))
        return self.img.shape[1],self.img.shape[0]
    @frame_size.setter
    def frame_size(self,new_size):
        self.make_img(new_size)

    @property
    def frame_rates(self):
        return range(30,121,30)

    @property
    def frame_sizes(self):
        return ((320,240),(640,480),(1280,720),(1920,1080))

    @property
    def frame_rate(self):
        return self.fps

    @frame_rate.setter
    def frame_rate(self,new_rate):
        self.fps = new_rate

    @property
    def name(self):
        return 'ofxPublishScreen Capture'
