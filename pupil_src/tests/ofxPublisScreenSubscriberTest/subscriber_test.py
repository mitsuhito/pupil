import zmq
import time
import cv2
import numpy as np

jpeg_buffer = None

def main():
    """ main method """
    print("main()::")
    # Prepare our context and publisher
    context    = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.connect("tcp://192.168.20.204:20000")
    #subscriber.setsockopt(zmq.SUBSCRIBE, b"B")
    subscriber.setsockopt(zmq.SUBSCRIBE,'')

    while True:
        # Read envelope with address
        jpeg_buffer = subscriber.recv()

        nparr = np.fromstring(jpeg_buffer, np.uint8)
        img = cv2.imdecode(nparr, cv2.CV_LOAD_IMAGE_COLOR)

        #print type(img)

        cv2.imshow('image', img)
        cv2.waitKey(1)
        #cv2.destroyAllWindows()

        #print(str(len(jpeg_buffer))+"\n")

    # We never get here but clean up anyhow
    subscriber.close()
    context.term()

if __name__ == "__main__":
    main()
