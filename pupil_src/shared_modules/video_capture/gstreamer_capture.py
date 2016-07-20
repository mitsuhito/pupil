'''

Gstreamer backend (WIP)

# requirements
# brew install gstreamer gst-python gst-libav gst-plugins-base gst-plugins-bad gst-plugins-good gst-plugins-ugly
#
# sender pipeline
# gst-launch-1.0 videotestsrc is-live=true do-timestamp=true horizontal-speed=1 ! videoconvert ! vtenc_h264 ! video/x-h264,profile=high ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=9000 sync=false
#
# receiver pipeline (this backend)
# gst-launch-1.0 -v udpsrc port=5000 ! application/x-rtp,clock-rate=90000,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! osxvideosink


'''

import cv2
import numpy as np
from time import time,sleep
import datetime

#logging
import logging
logger = logging.getLogger(__name__)

#gstreamer-1.0
import gi
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '2.0')
from gi.repository import GObject, Gst, Gtk

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

class Gstreamer_Capture(object):
    """docstring for GstreamerCapture"""
    def __init__(self, port):
        super(Gstreamer_Capture, self).__init__()
        self.fps = 30
        self.presentation_time = time()
        self.make_img((640,480))
        self.frame_count = 0
        self.controls = []

        # init
        #GObject.threads_init()
        Gst.init(None)
        Gst.debug_set_active(True)
        Gst.debug_set_default_threshold(3)

        gst_pipeline_str = "udpsrc port=%d name=udp_src caps=application/x-rtp,clock-rate=90000,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! appsink name=app_sink emit-signals=true drop=true sync=false " % port

        # Create GStreamer pipeline
        #self.pipeline = Gst.parse_launch("udpsrc port=5000 name=udp_src caps=application/x-rtp,clock-rate=90000,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! appsink name=app_sink emit-signals=true drop=true sync=false ")
        self.pipeline = Gst.parse_launch(gst_pipeline_str)
        if self.pipeline == None:
            #print ("Failed to create pipeline")
            logger.error("Failed to create pipeline")
            #sys.exit(0)

        # Create bus to get events from GStreamer pipeline
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::error', self.on_error)

        # This is needed to make the video output in our DrawingArea:
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)

        self.sink = self.pipeline.get_by_name("app_sink")
        caps = Gst.caps_from_string("video/x-raw, format=(string){BGR, GRAY8}; video/x-bayer,format=(string){rggb,bggr,grbg,gbrg}")
        self.sink.set_property("caps", caps)

        # set callback
        self.sink.connect('new-sample', self.new_sample_cb)

        self.pipeline.set_state(Gst.State.PLAYING)
        logger.info("Start pipeline")

        #self.np_pixels = None


    def on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() == 'prepare-window-handle':
            print('prepare-window-handle')
        msg.src.set_property('force-aspect-ratio', True)
        msg.src.set_window_handle(self.xid)
        logger.info("on_sync_message bus:%s msg%s", bus, msg)

    def on_error(self, bus, msg):
        print('on_error():', msg.parse_error())
        logger.error("on_error %s", msg.parse_error())


    def new_sample_cb(self, appsink):
        #print("new_sample_cb::", appsink)
        sample = appsink.emit('pull-sample')
        buf = sample.get_buffer()
        caps = sample.get_caps()
        # print(caps.get_structure(0).get_value('format'))
        # print(caps.get_structure(0).get_value('height'))
        # print(caps.get_structure(0).get_value('width'))
        # print(buf.get_size())

        # image type conversion
        arr = np.ndarray( (caps.get_structure(0).get_value('height'), caps.get_structure(0).get_value('width'), 3),
        buffer=buf.extract_dup(0, buf.get_size()),
        dtype=np.uint8)

        # embed time stamp string
        now = datetime.datetime.now()
        ts_str = now.strftime("%Y %m %d %H:%M:%S.") + "%04d" % (now.microsecond // 1000)
        #cv2.putText(arr, ts_str, (10,20), cv2.FONT_HERSHEY_PLAIN, 1, (0,0,0))

        # for debug
        #cv2.imshow('frame',arr)

        self.img = cv2.resize(arr, (640,480), interpolation=cv2.INTER_LANCZOS4)

        #self.np_pixels = arr
        return Gst.FlowReturn.OK


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
        return Frame(now,self.img.copy(),frame_count)

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
        return 'Gstreamer Capture'
