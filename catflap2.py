import time
import RPi.GPIO as io
import syslog

"""
This version of the solution simply tracks the opening and closing of each of the two flaps
"""
syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)

# Set our debounce timer to an initial value that makes sense
time_stamp_inner = time.time()
time_stamp_outer = time.time()

Inner_door_pin = 24
Outer_door_pin = 23

# Setup IO
io.setmode(io.BCM)
io.setup(Inner_door_pin, io.IN, pull_up_down=io.PUD_UP)  # activate input with PullUp
io.setup(Outer_door_pin, io.IN, pull_up_down=io.PUD_UP)  # activate input with PullUp


def log(message):
    syslog.syslog(syslog.LOG_INFO, message)


def catflap_callback_inner(pin):
    """
        This function is called by the RPi.GPIO library when an interrupt
        occurs, set up by the add_event_detect call in __init__.
        Interrupts are very efficient compared to polling for low latency
        applications - we don't want delay between the cat appearing and
        the shutter on the camera!
        """
    global time_stamp_inner

    # When was the interrupt triggered?
    time_now = time.time()
    # Read and store the current state of the pin - high or low
    current_value = io.input(pin)
    # Log the event
    # print( "GPIO event (%s) - time_now %s, last activation at %s" % (io.input(pin), time_now, time_stamp_inner))

    if current_value == io.LOW:
        # If the pin is low, the flap is closed!

        # Take a note
        print("Inner Flap closed at %s" % time.time())

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

    # When was the interrupt triggered?
    time_now = time.time()
    # Read and store the current state of the pin - high or low
    current_value = io.input(pin)
    # Log the event
    # print( "GPIO event (%s) - time_now %s, last activation at %s" % (io.input(pin), time_now, time_stamp_outer))

    if current_value == io.LOW:
        # If the pin is low, the flap is closed!

        # Take a note
        print("Outer Flap closed at %s" % time.time())

    elif current_value == io.HIGH:
        # If the pin is high, the flap has opened!
        # But it might be the case that we already saw the flap open and
        # what we're actually seeing is the flap swinging past the sensor
        # as it settles back down to close. Let's check!

        if (time_now - time_stamp_outer) >= 2:
            # If it's been two seconds since we last saw a flap open event
            # then we're interested in this one as a new event

            print("Outer Flap opened (not bounce) at %s" % time.time())
            # Let's store the time this event happened
            time_stamp_outer = time_now



        else:
            # If it's been less than two seconds since the last cat,
            # this is probably just the flap swinging past the sensor

            # But keep a record to help us figure out problems
            print("Outer Debounce filtered an event")


io.add_event_detect(Inner_door_pin, io.BOTH, callback=catflap_callback_inner, bouncetime=200)
io.add_event_detect(Outer_door_pin, io.BOTH, callback=catflap_callback_outer, bouncetime=200)

while True:
    time.sleep(0.5)
