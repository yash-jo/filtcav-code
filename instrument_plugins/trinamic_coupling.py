"""
Created on Mon Aug 5 2019

@author: Yash
"""
import TMCL
from serial import Serial
import time
from instrument import Instrument
import types
import logging

class trinamic_coupling(Instrument):
    '''
    For controling the coupling rate of the microwave input to the cavity by rotating the antenna
    '''

    def __init__(self,name, mid=0, port='COM3'):

        logging.info(__name__ + ' : Initializing instrument Trinamic TMCL motor')
        Instrument.__init__(self, name, tags=['physical'])

        self.connect_motor(mid, port)

    def connect_motor(self, mid, port): 
        serial_port = Serial(port, timeout=2)
        bus = TMCL.connect(serial_port)

        motor = bus.get_motor(mid)
        self.motor = motor

    def set_speed(self, speed):
        self.speed = speed

    def rotate_right(self):
        self.motor.rotate_right(self.speed)

    def rotate_left(self):
        self.motor.rotate_left(self.speed)

    def stop(self):
        self.motor.stop()

    def move_relative(self, position):
        self.motor.move_relative(position)
        #while self.motor.axis.actual_position - self.motor.axis.target_position < 100:
         #   time.sleep(0.01)

    def move_absolute(self, position):
        self.motor.move_absolute(position)

    def remove(self):
        self.motor.bus.serial.close()
        Instrument.remove(self)

    def get_position(self):
        return self.motor.axis.actual_position
