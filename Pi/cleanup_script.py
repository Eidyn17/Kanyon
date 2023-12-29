#!/usr/bin/python3

import RPi.GPIO as GPIO

# Set up GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.OUT)
GPIO.setup(26, GPIO.OUT)

# Clean up GPIO
GPIO.output(27, GPIO.LOW)
GPIO.output(26, GPIO.LOW)
GPIO.cleanup()
