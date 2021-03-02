from instrument import Instrument
import visa
import logging
import types
from numpy import pi
import numpy as np
import time


class RS_ZNB20(Instrument):
    '''
    This is the python driver for the ZNB20

    Usage:
    Initialize with
    <name> = instruments.create('name', 'ZNB20', address='<GPIB address>', reset=True|False)
    '''
    def __init__(self, name, address, reset = False):
        '''
        Initializes the ZNB20
        Input:
            name (string)    : name of the instrument
            address (string) : TCPIP/GPIB address
            reset (bool)     : Reset to default values
        Output:
            None
        '''
        logging.debug(__name__ + ' : Initializing instrument')
        Instrument.__init__(self, name, tags=['physical'])
           
        self._address = address
        rm = visa.ResourceManager()
        self._visainstrument = rm.open_resource(self._address)
        
        self._zerospan = False
        
        self.add_parameter('span', flags=Instrument.FLAG_GETSET, units='Hz', minval=1, maxval=20e9-100e3, type=types.FloatType)
        self.add_parameter('centerfreq', flags=Instrument.FLAG_GETSET, units='Hz', minval=100e3, maxval=20e9, type=types.FloatType)
        self.add_parameter('startfreq', flags=Instrument.FLAG_GETSET, units='Hz', minval=100e3, maxval=20e9, type=types.FloatType)
        self.add_parameter('stopfreq', flags=Instrument.FLAG_GETSET, units='Hz', minval=100e3, maxval=20e9, type=types.FloatType)
        self.add_parameter('power', flags=Instrument.FLAG_GETSET, units='dBm', maxval=10.0, type=types.FloatType)
        self.add_parameter('averages', flags=Instrument.FLAG_GETSET, units='', maxval=100000, type=types.IntType)
        self.add_parameter('Average', flags=Instrument.FLAG_GETSET, option_list=['ON', 'OFF'], type=types.StringType)
        self.add_parameter('nop', flags=Instrument.FLAG_GETSET, units='', minval=1, maxval=100000, type=types.IntType)
        self.add_parameter('bandwidth', flags=Instrument.FLAG_GETSET, units='Hz', minval=1, maxval=1e6, type=types.FloatType)
        self.add_parameter('status', flags=Instrument.FLAG_GETSET, option_list=['ON', 'OFF'], type=types.StringType)
        self.add_parameter('reference', flags=Instrument.FLAG_GETSET, option_list=['INT', 'EXT'], type=types.StringType)
        self.add_parameter('convmode', flags=Instrument.FLAG_GETSET, option_list=['FUND', 'ARB'], type=types.StringType)
        self.add_parameter('convoffset', flags=Instrument.FLAG_GETSET, units='Hz', minval=-20e9, maxval=20e9, type=types.FloatType)
        self.add_parameter('identification', flags=Instrument.FLAG_GET, type=types.StringType)
        
#        self.add_parameter('zerospan', flags=Instrument.FLAG_GETSET, type=types.BooleanType)
        
        self.add_function ('Autoscale')
        self.add_function ('LOaboveRF')
        self.add_function ('LObelowRF')
        self.add_function ('centertomax')
        self.add_function ('centertomin')
        self.add_function ('edelay_auto')
        self.add_function ('run_cont')
        self.add_function ('get_all')
        self.add_function('reset')
#        self.add_function('get_freqpoints')
#        self.add_function('get_tracedata')
#        self.add_function('get_sweeptime')
        self.add_function('avg_clear')
        
        if reset :          
            self.reset()       
        self.get_all()

############################################################################
#
#            Methods
#
############################################################################

    def reset(self):
        '''
        Resets the instrument to default values
        Input:
            None
        Output:
            None
        '''
        logging.info(__name__ + ' : Resetting instrument')
        self._visainstrument.write('*RST')
        self.set_reference('EXT')

    def get_all(self):
        '''
        Get all parameters of the intrument
        Input:
            None
        Output:
            None
        '''
        logging.info(__name__ + ' : get all')
        self.get_power()
        self.get_centerfreq()
        self.get_span()
        self.get_startfreq()
        self.get_stopfreq()
        self.get_averages()
        self.get_Average()
        self.get_nop()
        self.get_bandwidth()
        self.get_status()
        self.get_reference()
        self.get_convmode()
        # self.get_convoffset() # not working quite well
        self.get_identification()

           
###########################################################################################################################################################################
#
#                                                           Communication with device
#
############################################################################################################################################################################          
                        
    def get_sweeptime(self):
        return float(self._visainstrument.query('sweep:time?'))
    
    def avg_clear(self):
        self._visainstrument.write('average:clear')
        
    def meas_over(self):
        return bool(int(self._visainstrument.query('*ESR?')))	
    
    def measure(self):
        '''
        init measurement
        Input:         
        Output:
            None
        '''
        logging.info(__name__ + ' : start to measure and wait till it is finished')
        self._visainstrument.write('initiate:cont off')
        self._visainstrument.write('init:imm ')
        self._visainstrument.write('*OPC')
        
    # get_tracedata part   
    
    def get_tracedata(self):
        '''
        Get the data of the current trace
        Input:
            None
        Output:
            complex trace values
        '''
        dstring=self._visainstrument.query('calculate:Data? Sdata')
        self._visainstrument.write('init:cont on')
        real, im= np.reshape(np.array(dstring.split(','),dtype=float),(-1,2)).T
        return real + im * 1j              
      
    def get_freqpoints(self, query = False):      
        return np.linspace(self.get_startfreq(query),self.get_stopfreq(query),self.get_nop(query))

    def run_cont(self):
        self._visainstrument.write('init:cont on')

#########################################################
#
#                  Write and Read from VISA
#
#########################################################
    def tell(self, cmd):
        self._visainstrument.write(cmd)
    def query(self, cmd):
        res= self._visainstrument.query(cmd)
        print res
        return res
#########################################################
#
#                Frequency
#
#########################################################
    def do_set_centerfreq(self, centerfreq=1.):
        '''
            Set the center frequency of the instrument
            Input:
                frequency (float): Center frequency at which the instrument will measure [Hz]
            Output:
                None
        '''
        
        logging.info(__name__+' : Set the frequency of the intrument')
        self._visainstrument.write('frequency:center '+str(centerfreq))
        self.get_startfreq()
        self.get_stopfreq()

    def do_get_centerfreq(self):
        '''
            Get the frequency of the instrument
            Input:
                None
            Output:
                frequency (float): frequency at which the instrument has been tuned [Hz]
        '''
        
        logging.info(__name__+' : Get the frequency of the intrument')
        return self._visainstrument.query('frequency:center?')

    def do_set_span(self, span=1.):
        '''
            Set the frequency span of the instrument
            Input:
                frequency (float): Frequency span at which the instrument will measure [Hz]
            Output:
                None
        '''
        
        logging.info(__name__+' : Set the frequency of the intrument')
        self._visainstrument.write('frequency:span '+str(span))
        self.get_startfreq()
        self.get_stopfreq()


    def do_get_span(self):
        '''
            Get the frequency of the instrument
            Input:
                None
            Output:
                frequency (float): frequency at which the instrument has been tuned [Hz]
        '''      
        logging.info(__name__+' : Get the frequency of the intrument')
        return self._visainstrument.query('frequency:span?')


    def do_set_startfreq(self, startfreq=1.):
        '''
            Set the start frequency of the instrument
            Input:
                frequency (float): Frequency at which the instrument will be tuned [Hz]
            Output:
                None
        '''      
        logging.info(__name__+' : Set the frequency of the intrument')
        self._visainstrument.write('frequency:start '+str(startfreq))
        self.get_centerfreq()
        self.get_span()



    def do_get_startfreq(self):
        '''
            Get the frequency of the instrument
            Input:
                None
            Output:
                frequency (float): frequency at which the instrument has been tuned [Hz]
        '''       
        logging.info(__name__+' : Get the frequency of the intrument')
        return self._visainstrument.query('frequency:start?')

    def do_set_stopfreq(self, stopfreq=1.):
        '''
            Set the stop frequency of the instrument
            Input:
                frequency (float): stop frequency at which the instrument will be tuned [Hz]
            Output:
                None
        '''       
        logging.info(__name__+' : Set the stop frequency of the intrument')
        self._visainstrument.write('frequency:stop '+str(stopfreq))
        self.get_centerfreq()
        self.get_span()


    def do_get_stopfreq(self):
        '''
            Get the stop frequency of the instrument
            Input:
                None
            Output:
                frequency (float): stop frequency at which the instrument has been tuned [Hz]
        '''       
        logging.info(__name__+' : Get the stop frequency of the intrument')
        return self._visainstrument.query('frequency:stop?')

    def do_set_convoffset(self, convoffset):
        '''
            Set the conversion offset of the instrument
            Input:
                frequency offset (float): port 2 will measure at port 1 freq + offset [Hz]
            Output:
                None
        '''       
        logging.info(__name__+' : Set the conversion offset of the intrument')
        
        self._visainstrument.write('sour:freq2:conv:arb:ifr 1,1, {}, SWE'.format(convoffset))
        #time.sleep(0.5)
        self.get_convmode()


    def do_get_convoffset(self):
        '''
            Get the conversion offset of the instrument
            Input:
                None
            Output:
                frequency offset (float): port 2 will measure at port 1 freq + offset [Hz]
        '''       
        logging.info(__name__+' : Get the conversion offset of the intrument')
        # I could not find a way to actually query this number...
        # in doubt, just put it in normal mode?
        self.set_convoffset(0)
        self.set_convmode('fund')
        return 0

#########################################################
#
#                Power
#
#########################################################

    def do_set_power(self, power=-10):
        '''
            Set the power of the instrument
            Input:
                power (float): power at which the instrument will be tuned [dBm]
            Output:
                None
        '''        
        logging.info(__name__+' : Set the power of the intrument')
        self._visainstrument.write('source:power '+str(power))

    def do_get_power(self):
        '''
            Get the power of the instrument
            Input:
                None
            Output:
                power (float): power at which the instrument has been tuned [dBm]
        '''       
        logging.info(__name__+' : Get the power of the intrument')
        return self._visainstrument.query('source:power?')

#########################################################
#
#                Averages
#
#########################################################

    def do_set_averages(self, averages=1):
        '''
            Set the averages of the instrument
            Input:
                phase (float): averages at which the instrument will be tuned [rad]
            Output:
                None
        '''        
        logging.info(__name__+' : Set the averages of the intrument')
        self._visainstrument.write('average:count '+str(averages))
        if self.get_Average().upper() == 'ON':
            self._visainstrument.write('sens:sweep:count '+str(averages))

    def do_get_averages(self):
        '''
            Get the phase of the instrument
            Input:
                None
            Output:
                phase (float): averages of the instrument 
        '''       
        logging.info(__name__+' : Get the averages of the intrument')
        return int(self._visainstrument.query('average:count?'))

    def do_set_Average(self, status='off'):
        '''
        Set the output status of the instrument
        Input:
            status (string) : 'on' or 'off'
        Output:
            None
        '''
        logging.debug(__name__ + ' : set status to %s' % status)
        if status.upper() in ('ON', 'OFF'):
            status = status.upper()
        else:
            raise ValueError('set_status(): can only set on or off')
        if status == 'ON':
            self._visainstrument.write('sens:sweep:count '+str(self.get_averages()))
        else:
            self._visainstrument.write('sens:sweep:count 1')
        self._visainstrument.write('average %s' % status)
        

    def do_get_Average(self):
        '''
        Reads the output status from the instrument
        Input:
            None
        Output:
            status (string) : 'on' or 'off'
        '''
        logging.debug(__name__ + ' : get status')
        stat = int(self._visainstrument.query('average?'))

        if (stat==1):
          return 'ON'
        elif (stat==0):
          return 'OFF'
        else:
          raise ValueError('Output status not specified : %s' % stat)
        return


#########################################################
#
#                Bandwidth
#
#########################################################

    def do_set_bandwidth(self, bandwidth=1000):
        '''
            Set the power of the instrument
            Input:
                power (float): power at which the instrument will be tuned [dBm]
            Output:
                None
        '''        
        logging.info(__name__+' : Set the power of the intrument')
        self._visainstrument.write('sens:band '+str(bandwidth))
        
    def do_get_bandwidth(self):
        '''
            Get the BW of the instrument
            Input:
                None
            Output:
                BW (float): IF bandwidth
        '''
        
        logging.info(__name__+' : Get the BW of the intrument')
        return self._visainstrument.query('sens:band?')

#########################################################
#
#                Points
#
#########################################################

    def do_set_nop(self, points=1001):
        '''
            Set the number of points in the trace
            
            Input:
                points (int): number of points in the trace
            Output:
                None
        '''       
        logging.info(__name__+' : Set the power of the intrument')
        self._visainstrument.write('sens:sweep:points '+str(points))

    def do_get_nop(self):
        '''
            Get the number of points in the trace
            Input:
                None
            Output:
                points (int): the number of points in the trace
        '''
        
        logging.info(__name__+' : Get the BW of the intrument')
        return self._visainstrument.query('sens:sweep:points?')
                
#########################################################
#
#                Zerospan
#
#########################################################              
        
#    def do_set_zerospan(self,val):
#        '''
#        Zerospan is a virtual "zerospan" mode. In Zerospan physical span is set to
#        the minimal possible value (2Hz) and "averages" number of points is set.
#        Input:
#            val (bool) : True or False
#        Output:
#            None
#        '''
#        logging.debug(__name__ + ' : setting status to "%s"' % status)
#        if val not in [True, False]:
#            raise ValueError('set_zerospan(): can only set True or False')        
#        if val:
#          self._oldnop = self.get_points()
#          self._oldspan = self.get_span()
#          if self.get_span() > 0.002:
#            Warning('Setting ZVL span to 2Hz for zerospan mode')            
#            self.set_span(0.002)
            
#        av = self.get_averages()
#        self._zerospan = val
#        if val:
#            self.set_average(False)
#            self.set_averages(av)
#            if av<2:
#              av = 2
#        else: 
#          self.set_average(True)
#          self.set_span(self._oldspan)
#          self.set_points(self._oldnop)
#          self.get_averages()
#        self.get_points()
               
#    def do_get_zerospan(self):
#        '''
#        Check weather the virtual zerospan mode is turned on
#        Input:
#            None
#        Output:
#            val (bool) : True or False
#        '''
#        return self._zerospan

#########################################################
#
#                Status
#
#########################################################

    def do_get_status(self):
        '''
        Reads the output status from the instrument
        Input:
            None
        Output:
            status (string) : 'on' or 'off'
        '''
        logging.debug(__name__ + ' : get status')
        stat = int(self._visainstrument.query('output?'))

        if (stat==1):
          return 'ON'
        elif (stat==0):
          return 'OFF'
        else:
          raise ValueError('Output status not specified : %s' % stat)
        return

    def do_set_status(self, status='off'):
        '''
        Set the output status of the instrument
        Input:
            status (string) : 'on' or 'off'
        Output:
            None
        '''
        logging.debug(__name__ + ' : set status to %s' % status)
        if status.upper() in ('ON', 'OFF'):
            status = status.upper()
        else:
            raise ValueError('set_status(): can only set on or off')
        self._visainstrument.write('output %s' % status)
        
    def off(self):
        '''
        Set status to 'off'

        Input:
            None

        Output:
            None
        '''
        self.set_status('off')

    def on(self):
        '''
        Set status to 'on'

        Input:
            None

        Output:
            None
        '''
        self.set_status('on')

    def do_get_reference(self):
        '''
        Reads the reference oscillator from the instrument
        Input:
            None
        Output:
            reference (string) : 'int' or 'ext'
        '''
        logging.debug(__name__ + ' : get reference')
        stat = str(self._visainstrument.query('rosc?'))

        if (stat=='INT\n'):
          return 'INT'
        elif (stat=='EXT\n'):
          return 'EXT'
        else:
          raise ValueError('Reference not specified : %s' % stat)
        return

    def do_set_reference(self, status='EXT'):
        '''
        Set the reference oscillator of the instrument
        Input:
            reference (string) : 'int' or 'ext'
        Output:
            None
        '''
        logging.debug(__name__ + ' : set reference to %s' % status)
        if status.upper() in ('INT', 'EXT'):
            status = status.upper()
        else:
            raise ValueError('set_reference(): can only set int or ext')
        self._visainstrument.write('ROSC %s' % status)

    def do_get_convmode(self):
        '''
        Reads the conversion mode from the instrument
        Input:
            None
        Output:
            conv mode (string) : 'fund' or 'arb'
        '''
        logging.debug(__name__ + ' : get conversion mode')
        stat = self._visainstrument.query('sense:freq:conv?')

        if (stat=='FUND\n'):
          return 'FUND'
        elif (stat=='ARB\n'):
          return 'ARB'
        else:
          raise ValueError('Conversion mode not specified : %s' % stat)
        return

    def do_set_convmode(self, status='FUND'):
        '''
        Set the conversion mode of the instrument
        Input:
            conv mode (string) : 'fund' or 'arb'
        Output:
            None
        '''
        logging.debug(__name__ + ' : set conversion mode to %s' % status)
        if status.upper() in ('FUND', 'ARB'):
            status = status.upper()
        else:
            raise ValueError('set_convmode(): can only set fund or arb')
        if status=='FUND':
            self.set_convoffset(0)
        self._visainstrument.write('sense:freq:conv ' + status)

############################################################################
#
#            Change display settings
#
############################################################################
     
    def yscale_auto(self, tr=1):
        '''
        Set the scale of y axis automatically for a given trace
        
        Input:
            tr (int): trace number, defaults to 1
        Output:
            None
        '''
        comstr = "disp:trac{}:y:auto once".format(tr)
        self._visainstrument.write(comstr)
        # for some mysterious undocumented reason, the continuous measurement stops after the auto scaling
        self._visainstrument.write('initiate:cont on')

    def yscale_auto_alldiag(self):
        '''
        Set the scale of y axis automatically for all diagrams
        
        Input:
            None
        Output:
            None
        '''
        listdiagtrac = self._visainstrument.query("disp:cat?") # get all traces
        listdiagtrac = listdiagtrac.strip("'") # removes annoying '
        diags = listdiagtrac.split(',')[0::2] # takes only diag numbers (not names)
        comstr = "disp:wind{}:trac:y:auto once"
        for d in diags:
            self._visainstrument.write(comstr.format(d))
        # for some mysterious undocumented reason, the continuous measurement stops after the auto scaling
        self._visainstrument.write('initiate:cont on')

    Autoscale = yscale_auto_alldiag

    def yscale_pdiv(self, pdiv, d=1, tr=1):
        '''
        Set the scale of y axis to a number per division, for a given trace
        
        Input:
            pdiv (float): number of dB or radians  per division
            d (int): diagram number, defaults to 1
            tr (int): trace number, defaults to 1
        Output:
            None
        '''
        comstr = "disp:wind{0}:trac{1}:y:pdiv {2}".format(d, tr, pdiv)
        self._visainstrument.write(comstr)
        
    def edelay_auto(self):
        """
        Automatically offsets phase by fitting delay
        """
        self._visainstrument.write('corr:edelay:auto once')
    
    
    
    def centertomin(self):
        '''
        Search for min with marker, center sweep to the value, and turn off marker
        
        Input:
            None
        Output:
            None
        '''
        self._visainstrument.write("calc:mark on") 
        self._visainstrument.write("calc:mark:func:exec min")
        self._visainstrument.write("calc:mark:func:center")
        self._visainstrument.write("calc:mark off")
        # update sweep values
        self.get_startfreq()
        self.get_stopfreq()
        self.get_centerfreq()
        
    def centertomax(self):
        '''
        Search for min with marker, center sweep to the value, and turn off marker
        
        Input:
            None
        Output:
            None
        '''
        self._visainstrument.write("calc:mark on") 
        self._visainstrument.write("calc:mark:func:exec max")
        self._visainstrument.write("calc:mark:func:center")
        self._visainstrument.write("calc:mark off")
        # update sweep values
        self.get_startfreq()
        self.get_stopfreq()
        self.get_centerfreq()
        
############################################################################
#
#            Local oscillator and others
#
############################################################################
        
    def LObelowRF(self):
        '''
        Places LO below the RF frequencies: LO < RF
        
        Input:
            None
        Output:
            None
        '''
        self._visainstrument.write('freq:sban neg')
    
    def LOaboveRF(self):
        '''
        Places LO above the RF frequencies: LO > RF
        
        Input:
            None
        Output:
            None
        '''
        self._visainstrument.write('freq:sban pos')
    
    def clearerrors(self):
        '''
        Clears all errors from the buffer and returns them.
        
        Input:
            None
        Output:
            List of erors as one comma-separated string
        '''
        errs = self._visainstrument.query('syst:err:all?')
        self._visainstrument.write('syst:err:disp off')
        return errs

#########################################################
#
#
#                IDN
#
#
#########################################################
    def do_get_identification(self):
        '''
        Reads identification number

        Input:
            None

        Output:
            IDN (string) 
        '''
        logging.debug(__name__ + ' : get status')
        idn = self._visainstrument.query('*IDN?')

        return idn
