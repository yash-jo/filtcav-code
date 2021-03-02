'''
fc_tune.py
Written by Yash Joshi
February 2021
'''

import numpy as np
import matplotlib.pyplot as plt
import misc
import peakutils as pt
from time import sleep
from scipy.optimize import minimize


#The experimental setup on which this code was first run uses the Python based measurement environemnt called QTlab, which can be downloaded from - https://github.com/heeres/qtlab
import qt
#The user may want to change the code to be compatible with their own operating python environment

#Library for a VNA measurement within QTlab
import meas_vna as netw

#Library to take the VNA trace and find the resonances (Provided)
import meas_findRes as rs

#Getting the instruments within the QTlab environment
zls = qt.instruments.get('zls') #Linearised motor for changing the length
tnm = qt.instruments.get('tnm') #Rotary motor for changing the coupling
vna = qt.instruments.get('vna') #Vector network analyser



### GLOBAL PARAM
tnm.set_speed(15) # Coupling motor speed
err_depth = 10 ** -3 # Error we want in tuning the resonance depth - E_D in eq (3) of the manuscript
err_lin = 1e4 #  Error we want in tuning the resonance frequency - E_\omega in eq (3) of the manuscript

def fine_tune_nm(fr, verbose = False, lin_span = 0.5, coup_span = 0.1*2*np.pi, small_change=True, scan_coupling = False, plot = False, hold = True, label = None):
    '''
    Fine tuning with Nelder mead algorithm using linear motor (zls) and a stepper motor (tnm)

    lin_span:   Attenuatoin span of initial simplex
    coup_span:    Phase span of initial simplex
    min_ints:   Minimal number of iterations
    scan_coupling: 

    '''

    qt.mstart() #QTlab starts measurement
    settings = netw.setoutrange() # Setting the VNA outside the desired tuning range and saving the previous parameters

    # Initializing and defining the variables and parameters
    global x_min, level_min, nstep, vnaspan
    x_min = [0,0]
    level_min = 0
    nstep = 0
    vnaspan = 200e6 #200 MHz
    global levels_its
    levels_its = []
    zls.step_to_mm = 0.047625e-3 #zaber motor specification 

    #Defining what the algorithm should physically when a new point is interpolated by the Nelder Mead
    def parameter_changer(x):
        zls.move_abs_mm(x[0])
        tnm.move_absolute(x[1])
        tnm.wait()

        #while tnm.speed():
        #    qt.msleep(0.2*delay)

    def f(x):
        '''
            Evaluate the cost functiona again and terminate the algorithm if sufficient depth is reached
        '''

        parameter_changer(x) #Update to new point

        global x_min, level_min, vnaspan

        level = costfunction(fr, span=vnaspan)
        print 'Cost = ', level
        levels_its.append([x[0], x[1], level])
        lp = tone_depth_lin(fr)['depth']
        if lp <err_depth:
            print 'Level reached'
            raise Exception('Termination!!!')
        if level < level_min:
            level_min = level
            x_min = x

        return level


    # setup of initial condition
    if not small_change:
        #Lookup the position in the lookup table
        poses = np.flip(position_lookup(fr))
        zls.move_abs_mm(poses[0])

        #Fine tune just by detecting a resonant mode close by and moving it closer to desired frequency
        lin_stage_fine_tune(fr) 
        lin_ini = zls.current_position()
    else:
        lin_ini = zls.current_position() 

    if scan_coupling:
        #Scan the pin coupler angle over 360 degrees
        scan_coup(fr)
        coup_ini = tnm.get_position()
    else:
        coup_ini = tnm.get_position()

    x0 = [lin_ini, coup_ini] #Define the intial point

    xublin = lin_ini + lin_span
    xliblin = lin_ini - lin_span
    initial_simplex = [[x0[0], x0[1]],
                       [x0[0] - 0.1, x0[1]],
                       [x0[0], x0[1] + 0.05*coup_span]] # 3 points in the desirable neighbourhood of the parameter space


    print initial_simplex


    def callback(xk):
        ''' 
            Function that gets called after every iteration, does several things-
            1.counts number of steps
            2.reduces the VNA span to focus on the desired frequency
            3.terminates if sufficient depth level is attained
        '''
        global nstep, vnaspan
        nstep +=1
        print nstep
        if nstep>5: vnaspan = 100e6
        if nstep>20: vnaspan = 50e6
        vna.set_span(vnaspan)
        set_vna(fr)
        #print xk
        # val = [zls.current_position(), tnm.get_postion()]
        global x_min, level_min
        level = tone_depth_lin(fr)['depth']
        sleep(0.3)
        if level <err_depth:
            print 'level reached'
            raise Exception('Termination!!!')


    try:
        #Main Nelder mead function call
        res = minimize(f, x0,method = 'nelder-mead',tol = 0.01,callback = callback,
                       bounds = ((xliblin, xublin),(0, None)),
                       options = {'initial_simplex': initial_simplex,
                                  'disp': verbose,
                                  'maxiter': 40})
        force_termination = False
        
        qt.msleep()
    except Exception as inst:
        if not str(inst) == 'Termination!!!':
            raise
        force_termination = True

    netw.setbackrange(settings) #Setting the VNA back where we started from 
    vna.set_centerfreq(fr)
    qt.mend() #QTlab ends measurement
    return levels_its

def position_lookup(fr):
    '''
        Lookup the resonance modes from the table
    '''
    fr = fr/1e9
    res_filt = np.genfromtxt(r'lookuptble.csv', delimiter=',')  
    lookup = {}
    lookup['Position (mm)'] = res_filt.T[1]
    lookup['Frequency (GHz)'] = res_filt.T[0]

    lst = lookup['Frequency (GHz)']
    idx = [list(lst).index(x) for x in lst if np.abs(x - fr) < 0.01] #Finding the position
    print(idx)

    #No suitable resonances in certain frequency ranges
    if idx == []:
        idx = np.abs(lookup['Frequency (GHz)'] - fr).argmin()
        print('Warning: You are trying to set the filter cavity in an undesirable frequency.')
        return []

    positions = list(lookup['Position (mm)'][idx])
    positions = sorted(positions)
    # Multiple possible resonances- choose the closest one
    poses = positions[:1]
    for i in positions[1:]:
        if i >= poses[-1] + 1.8:
            poses.append(i)
    return poses


def lin_stage_fine_tune(fr, span = 500e6):
    '''
        Fine tune just by detecting a resonant mode close by and moving it closer to desired frequency
    '''
    sets = netw.setoutrange() #Setting the VNA outside the desired tuning range and saving the previous parameters
    scan_coup(fr) #Maximize resonance depths
    resonances = res_detect(fr - 5*span / 10., fr + 5*span / 10., rbw=5e4)
    meas = np.array([tone_depth_lin(frs) for frs in resonances])
    depths = np.array([mea['depth'] for mea in meas]) #Find tone depths
    resonances = np.array([1e9*mea['Frequency'] for mea in meas])
    print meas, depths, resonances
    idx = np.argmin(depths) 
    sel_res = resonances[idx] #select resonances to fit
    print 're', sel_res
    delf = fr - sel_res
    m = 0

    #Fine tuning while repeatedly minimizing the frequency difference
    while abs(delf) > 1e6:
        set_vna(sel_res);vna.set_span(30e6)
        sleep(0.3)
        move_adapt(delf)
        sel_res = res_detect(sel_res - 30e6, sel_res+30e6, rbw=1e5)
        m += 1
        if m>25: break
        if len(sel_res) == 0:
            print 'tuning'
            tune_linstage(fr, thresh=1e6)
            break
        print sel_res
        sel_res = sel_res[0]
        delf = fr - sel_res


    netw.setbackrange(sets) #Setting back the VNA resonances
    return resonances, depths


def scan_coup(fr, span= 200e6,  step=np.pi/100, thetaspan=2*np.pi):
    '''
    Scans the coupling over 360 degrees and finds the best angle for which the depth is maximum, which can then be given as the initial simplex of the Nelder-Mead algorithm.
        fr:center frequency
        span: span of the VNA
        step: minimum step size in angle during the scan 
        thetaspan:range of theta values over which to scan the couplings.  
    '''
    qt.mstart()
    vna.set_span(span)
    set_vna(fr)
    # tnm.move_absolute(0)
    # tnm.wait()
    current_position = tnm.get_position()
    # print "zero set",current_position
    depths = []
    positions = np.arange(current_position,current_position+thetaspan, step)
    for i in range(int(thetaspan/step) +1):
        dep = tone_depth(fr, rbw = 1e6)['depth (dB)']
        if dep < -25: break
        depths.append(dep)
        tnm.move_relative(step)
        tnm.wait()
        print tnm.get_position()
    qt.mend()
    # return target_position, min(depths), new_pos - target_position



def tone_depth_lin(centerfreq, span=0.1e6, rbw =1e5):
    tone = {}
    sets = netw.setoutrange()
    vna.set_span(span)
    # vna.set_nop(3000)
    # vna.set_centerfreq(centerfreq)
    set_vna(centerfreq, rbw)
    freqs, trace = netw.trace(measure=1, get_result=1, make_plot=0, make_data=0)
    amps = np.abs(trace)**2
    # ampdb = 10*np.log10(amps)
    # depth = np.min(ampdb)
    idx = np.argmin(abs(freqs-centerfreq/1e9))
    depth = amps[idx]
    netw.setbackrange(sets)
    # resfreq = freqs[np.argmin(ampdb)]
    # tone['Frequency'] = resfreq*1e9
    tone['depth'] = depth
    tone['Frequency'] = freqs[np.argmin(amps)]
    tone['trace'] =[freqs, trace]
    return tone



def costfunction(fr, span= 200e6):
    '''
        fr: Tuning frequency
        span: span over which to find resonances
    '''

    #Detecting resonances within a cetain range
    resonances = res_detect(fr - span/2. , fr + span/2., rbw = 5e4)

    #Measureing depths of resonances
    meas = np.array([tone_depth_lin(frs) for frs in resonances])

    resonances = np.array([1e9*mea['Frequency'] for mea in meas])
    depths = np.array([mea['depth'] for mea in meas])


    dic =  {}
    dic['lin'] =  (resonances - fr)**2/err_lin**2 #Frequency dependent term in the cost function
    dic['dep'] = depths**2/err_depth**2 #Coupling dependent term in the cost function
    dic['tot'] = np.min(dic['lin'] + dic['dep']) #Total cost function

    vna.Autoscale()

    return dic['tot'] 


def res_detect(startfreq, stopfreq, rbw = 5e4, doplot=False):
    ''' 
    Detects resonances within the given frequency range
        rbw: bandwidth

    '''
    #Acquiring the VNA trace, and calculating the phase gradient 
    vnadata = rs.phasegrad_VNA(fmin=startfreq, fmax=stopfreq, vna_power=10, points=1, max_nop=5e4, resolution=rbw, docomment=0, doplot=0, outrange=1)

    freqeuncies = vnadata['Frequency (Hz)']
    phase_gradient = vnadata['Phase gradient (rad/Hz)']

    #Detecting the peaks in the gradient and labeling them as resonoances
    peaksdata = rs.find_peaks(freqs=freqeuncies, grads=phase_gradient, dist_peaks=1e5, svp=4, winlen=1e9, doplot=doplot)
    res_freqs = peaksdata['Peak freqs filt']

    return np.array(res_freqs)


def set_vna(fr, rbw=1e5):
    '''
        fr:center frequency
        rbw: bandwidth
    '''
    vna_span = vna.get_span()
    nop = 5 * vna_span / rbw #To make sure we have sufficient points and bandwidth ratio to span the whole frequency range
    vna.set_bandwidth(rbw)
    vna.set_centerfreq(fr)
    vna.set_nop(nop)
    vna.set_power(10)


