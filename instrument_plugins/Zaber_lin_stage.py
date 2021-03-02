# created by Amir and AmirAli

from instrument import Instrument
import types
import ctypes
from zaber.serial import AsciiSerial, AsciiDevice, AsciiCommand, AsciiReply
import time
import logging
from numpy import pi

class Zaber_lin_stage(Instrument):
    '''
        None
    '''

    def __init__(self, name, device_number=1):
        '''
           None
        '''
        logging.info(__name__ + ' : Initializing instrument Zaber Linear Stage')
        Instrument.__init__(self, name, tags=['physical'])
        
        self.add_parameter('position',
            units='',
            type=types.IntType,
            flags=Instrument.FLAG_GETSET + Instrument.FLAG_GET_AFTER_SET)
        
        self.add_parameter('device_number', flags=Instrument.FLAG_GET, type=types.StringType)
        
        self._device_number = device_number
        self.step_to_mm = 0.047625e-3

        self.client = AsciiDevice(AsciiSerial("COM4"), device_number)

    def poll_until_idle(self):
        reply = self.client.poll_until_idle()

    def home(self):
        reply = self.client.home()

    def move_rel(self, distance, blocking = True):
        reply = self.client.move_rel(distance, blocking)

    def move_rel_mm(self, distance, blocking = True):
        reply = self.client.move_rel(int(distance/self.step_to_mm), blocking)

    def move_abs(self, position, blocking = True):
        reply = self.client.move_abs(position, blocking)

    def move_abs_mm(self, position, blocking = True):
        reply = self.client.move_abs(int(position/self.step_to_mm), blocking)

    def move_vel(self, speed, blocking = False):
        reply = self.client.move_vel(speed, blocking)

    def move_vel_distance(self, vel, distance):
        x0 = self.client.get_position()
        speed = int(vel / self.step_to_mm)
        d = int(distance / self.step_to_mm)
        reply = self.client.move_vel(vel)
        while(1):
            x = self.client.get_position()
            if(abs(x-x0)>d):
                self.client.stop()
                breaktnm

    def stop(self):
        reply = self.client.stop()

    def current_status(self):
        reply = self.client.get_status()

    def current_position(self):
        reply = self.client.get_position()
        return reply