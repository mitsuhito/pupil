#!/usr/bin/python3

# this example shows how to receive, decode and display a RTP h264 stream
# I'm using it to receive stream from Raspberry Pi
# This is the pipeline :
# gst-launch-1.0 -e -vvvv udpsrc port=5000 ! application/x-rtp, payload=96 ! rtpjitterbuffer ! rtph264depay ! avdec_h264 ! fpsdisplaysink sync=false text-overlay=false
#
# requirements
# brew install gstreamer gst-python gst-libav gst-plugins-base gst-plugins-bad gst-plugins-good gst-plugins-ugly
#
# sender
# gst-launch-1.0 videotestsrc is-live=true do-timestamp=true horizontal-speed=1 ! videoconvert ! vtenc_h264 ! video/x-h264,profile=high ! h264parse ! rtph264pay config-interval=1 pt=96 ! udpsink host=127.0.0.1 port=5000 sync=false
#
# receiver
# gst-launch-1.0 -v udpsrc port=5000 ! application/x-rtp,clock-rate=90000,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! osxvideosink


import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, Gtk

# Needed for window.get_xid(), xvimagesink.set_window_handle(), respectively:
#from gi.repository import GdkX11, GstVideo

import cv2
import numpy


GObject.threads_init()
Gst.init(None)
Gst.debug_set_active(True)
Gst.debug_set_default_threshold(3)


class RTPStream:
    def __init__(self):
        self.window = Gtk.Window()
        self.window.connect('destroy', self.quit)
        self.window.set_default_size(800, 450)

        self.drawingarea = Gtk.DrawingArea()
        self.window.add(self.drawingarea)

        # Create GStreamer pipeline
        self.pipeline = Gst.Pipeline()

        # udpsrc port=5000 ! application/x-rtp,clock-rate=90000,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! osxvideosink
        #self.pipeline = Gst.parse_launch ("rpicamsrc name=src ! video/x-h264,width=320,height=240 ! h264parse ! mp4mux ! filesink name=s")
        self.pipeline = Gst.parse_launch("udpsrc port=5000 name=udp_src caps=application/x-rtp,clock-rate=90000,payload=96 ! rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! appsink name=app_sink emit-signals=true drop=true sync=false ")
        if self.pipeline == None:
            print ("Failed to create pipeline")
            sys.exit(0)

        # Create bus to get events from GStreamer pipeline
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::error', self.on_error)

        # This is needed to make the video output in our DrawingArea:
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)

        # # Create GStreamer elements
        # self.udpsrc = Gst.ElementFactory.make('udpsrc', None)
        # print(self.udpsrc)
        # self.udpsrc.set_property('port', 5000)
        # self.buffer = Gst.ElementFactory.make('rtpjitterbuffer',None)
        # self.depay = Gst.ElementFactory.make('rtph264depay', None)
        # self.decoder = Gst.ElementFactory.make('avdec_h264', None)
        # #self.sink = Gst.ElementFactory.make('autovideosink', None)
        # self.convert = Gst.ElementFactory.make('videoconvert', None)
        # self.sink = Gst.ElementFactory.make('appsink', None)
        # self.sink.set_property('emit-signals', True)
        # self.sink.set_property('sync', False)
        # self.sink.set_property('drop', True)

        #self.udpsrc.link_filtered(self.depay, Gst.caps_from_string("application/x-rtp, payload=96"))

        self.sink = self.pipeline.get_by_name("app_sink")
        caps = Gst.caps_from_string("video/x-raw, format=(string){BGR, GRAY8}; video/x-bayer,format=(string){rggb,bggr,grbg,gbrg}")
        self.sink.set_property("caps", caps)

        self.sink.connect('new-sample', self.new_sample_cb)

        # #self.gdepay = Gst.ElementFactory.make('gdpdepay', 'gdepay')
        #
        # # Add elements to the pipeline
        # self.pipeline.add(self.udpsrc)
        # #self.pipeline.add(self.gdepay)
        # self.pipeline.add(self.buffer)
        # self.pipeline.add(self.depay)
        # self.pipeline.add(self.decoder)
        # #self.pipeline.add(self.convert)
        # self.pipeline.add(self.sink)
        #
        # self.udpsrc.link_filtered(self.depay, Gst.caps_from_string("application/x-rtp, payload=96"))
        # #self.gdepay.link(self.udpsrc)
        # self.depay.link(self.decoder)
        # self.decoder.link(self.sink)
        # #self.sink.link(self.convert)

    def new_sample_cb(self, appsink):
        print("new_sample_cb::", appsink)
        sample = appsink.emit('pull-sample')
        buf = sample.get_buffer()
        caps = sample.get_caps()
        print(caps.get_structure(0).get_value('format'))
        print(caps.get_structure(0).get_value('height'))
        print(caps.get_structure(0).get_value('width'))
        print(buf.get_size())


        arr = numpy.ndarray( (caps.get_structure(0).get_value('height'), caps.get_structure(0).get_value('width'), 3),
        buffer=buf.extract_dup(0, buf.get_size()),
        dtype=numpy.uint8)

        cv2.imshow('frame',arr)
        #self.out.write(arr)
        self.videoWriter.write(arr)
        return Gst.FlowReturn.OK

    def run(self):
        self.window.show_all()

        fps = 30
        #size = (int(cameraCapture.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)),
        #        int(cameraCapture.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT)))
        size = (320, 240)
        #self.videoWriter = cv2.VideoWriter('output.avi', cv2.VideoWriter_fourcc('I', '4', '2', '0'), fps, size)
        self.videoWriter = cv2.VideoWriter('output.avi', cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'), fps, size)

        # You need to get the XID after window.show_all(). You shouldn't get it
        # in the on_sync_message() handler because threading issues will cause
        # segfaults there.
        #self.xid = self.drawingarea.get_property('window').get_xid()
        self.pipeline.set_state(Gst.State.PLAYING)
        #cap = cv2.VideoCapture(self.pipeline)
        #print(cap)
        Gtk.main()

    def quit(self, window):
        self.pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit()
        self.videoWriter.release()

    def on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() == 'prepare-window-handle':
            print('prepare-window-handle')
        msg.src.set_property('force-aspect-ratio', True)
        msg.src.set_window_handle(self.xid)

    def on_error(self, bus, msg):
        print('on_error():', msg.parse_error())


rtpstream = RTPStream()
rtpstream.run()
