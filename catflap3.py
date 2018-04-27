import time
import datetime
import RPi.GPIO as io
import picamera
import argparse
from twython import Twython

# Set up our IO
io.setmode(io.BCM)
Inner_door_pin = 24
Outer_door_pin = 23
io.setup(Inner_door_pin, io.IN, pull_up_down=io.PUD_UP)  # activate input with PullUp
io.setup(Outer_door_pin, io.IN, pull_up_down=io.PUD_UP)  # activate input with PullUp

# Set our debounce timer to an initial value that makes sense
time_stamp_inner = time.time()
time_stamp_outer = time.time()

# Global which will hold the path of our image
final_path = None

cat_state = "inside"

# Camera Setup
camera = picamera.PiCamera()
camera.resolution = (2592, 1944)

# We can set EXIF tags here - record what camera model we are
camera.exif_tags['IFD0.Software'] = 'Tweeting Catflap 2.0'

# Turn off the LED
camera.led = False

# Pull out the twitter key from the commandline
parser = argparse.ArgumentParser()
parser.add_argument("key")
twitterKey = parser.parse_args()


def format_time(epoc_time):
    return datetime.datetime.fromtimestamp(epoc_time).strftime('%Y-%m-%d %H:%M:%S')


def tweet(message, file):
    api = Twython(twitterKey)

    photo = open(file, 'rb')

    print "Uploading photo to twitter...\n"
    media_status = api.upload_media(media=photo)

    print "Posting tweet with picture...\n"
    api.update_status(media_ids=[media_status['media_id']], status=message)
    print "Tweet Complete...\n"


def determine_state(current_state, event):
    # states are inside, exiting, outside, entering
    # events are inner_opening and outer_opening

    if current_state == "inside":
        if event == "inner_opening":
            return "exiting"
        elif event == "outer_opening":
            print "invalid state transition - was inside, got outer flap. Inruder!?"
            return "exiting"

    elif current_state == "exiting":
        if event == "inner_opening":
            return "exiting"
        elif event == "outer_opening":
            return "outside"


    elif current_state == "outside":
        if event == "inner_opening":
            print "invalid state transition - was outside, got inner flap. "
            return "outside"
        elif event == "outer_opening":
            return "entering"

    elif current_state == "entering":
        if event == "inner_opening":
            return "inside"
        elif event == "outer_opening":
            return "entering"


def catflap_callback_inner(pin):
    """
        This function is called by the RPi.GPIO library when an interrupt
        occurs, set up by the add_event_detect call in __init__.
        Interrupts are very efficient compared to polling for low latency
        applications - we don't want delay between the cat appearing and
        the shutter on the camera!
        """
    global time_stamp_inner
    global cat_state
    global final_path

    # When was the interrupt triggered?
    time_now = time.time()
    # Read and store the current state of the pin - high or low
    current_value = io.input(pin)
    # Log the event
    print("GPIO event inner (%s) - time_now %s, value is %s , last activation at %s" % (
        io.input(pin), format_time(time_now), current_value, format_time(time_stamp_inner)))

    if current_value == io.LOW:
        # If the pin is low, the flap is closed!

        # Take a note
        print("Inner Flap closed at %s" % format_time(time.time()))

    elif current_value == io.HIGH:
        # If the pin is high, the flap has opened!
        # But it might be the case that we already saw the flap open and
        # what we're actually seeing is the flap swinging past the sensor
        # as it settles back down to close. Let's check!

        if (time_now - time_stamp_inner) >= 2:
            # If it's been two seconds since we last saw a flap open event
            # then we're interested in this one as a new event
            print("Inner Flap opened (not bounce) at %s" % time.time())
            # Let's store the time this event happened
            time_stamp_inner = time_now

            cat_state = determine_state(cat_state, "inner_opening")
            print "Cat state is %s" % cat_state

            # Now we generate a filename based on the time, for instance
            # 20141007-200000.jpg (8pm Oct 7th 2014). This means we can
            # easily find out when a specific photo was taken!
            filename = "%s.jpg" % time.strftime("%Y%m%d-%H%M%S")
            # Now we prepend the filename with the path we're using
            # to store all our photos - in this case, /srv/cats
            final_path = "/srv/cats/%s" % filename

            # We're using the camera instance given to the class initially
            # which is being held open and ready for us - all we need
            # to do is ask it to capture an image to a path.
            # We configure the camera when we set up this class below.

            time.sleep(0.6)
            camera.capture(final_path)

            print("Photo Taken")

            if cat_state == "inside":
                tweet("Ginger has entered the building at %s" % format_time(time.time()), final_path)
                print("tweet")

        else:
            # If it's been less than two seconds since the last cat,
            # this is probably just the flap swinging past the sensor

            # But keep a record to help us figure out problems
            print("Debounce filtered an event")


def catflap_callback_outer(pin):
    """
        This function is called by the RPi.GPIO library when an interrupt
        occurs, set up by the add_event_detect call in __init__.
        Interrupts are very efficient compared to polling for low latency
        applications - we don't want delay between the cat appearing and
        the shutter on the camera!
        """
    global time_stamp_outer
    global cat_state
    global final_path

    # When was the interrupt triggered?
    time_now = time.time()
    # Read and store the current state of the pin - high or low
    current_value = io.input(pin)
    # Log the event
    print("GPIO event outer(%s) - time_now %s, last activation at %s" % (
        io.input(pin), format_time(time_now), format_time(time_stamp_outer)))

    if current_value == io.LOW:
        # If the pin is low, the flap is closed!

        # Take a note
        print("Outer Flap closed at %s" % format_time(time.time()))

    elif current_value == io.HIGH:
        # If the pin is high, the flap has opened!
        # But it might be the case that we already saw the flap open and
        # what we're actually seeing is the flap swinging past the sensor
        # as it settles back down to close. Let's check!

        if (time_now - time_stamp_outer) >= 2:
            # If it's been two seconds since we last saw a flap open event
            # then we're interested in this one as a new event

            print("Outer Flap opened (not bounce) at %s" % format_time(time.time()))
            # Let's store the time this event happened
            time_stamp_outer = time_now

            cat_state = determine_state(cat_state, "outer_opening")
            print "Cat state is %s" % cat_state

            if cat_state == "outside":
                tweet("Ginger has left the building at %s" % format_time(time.time()), final_path)
                print("tweet")

        else:
            # If it's been less than two seconds since the last cat,
            # this is probably just the flap swinging past the sensor

            # But keep a record to help us figure out problems
            print("Outer Debounce filtered an event")


io.add_event_detect(Inner_door_pin, io.BOTH, callback=catflap_callback_inner)
io.add_event_detect(Outer_door_pin, io.BOTH, callback=catflap_callback_outer, bouncetime=200)

while True:
    time.sleep(0.5)
