'''
fc_tune.py
Written by Philipp Uhrich
2019
'''

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal as sig
import peakutils
from peakutils.plot import plot as pplot
import os
import datetime
import misc

#QTlab and related libraries
import qt
import meas_vna as netw
import postprocessing_libs as ppl
import meas_switch as switch


def phasegrad_VNA(portpath='', fmin=2.6e9, fmax=8e9, resolution=1e4, max_nop=1e4, points=3, vna_power=-10, docomment=True, doplot = True, outrange=True):
    """Take VNA trace and identify possible microwave resonances
        Input:
            fmin, fmax: Start and end frequency (Hz) of VNA trace. Defaults to range which HEMT can resolve.
            resolution (int):   Frequency resolution. Defaults to 10kHz.
            max_nop (int):  Maximum acceptable nop for VNA trace. Defaults to 1e4. Maximum possible value is 1e5.
            points (int):   Amount of points desired within RBW. Defaults to 3.
            vna_power(int): Set vna power in dBm. Defaults to -10dBm
        Options:
            portpath (str): Directory in which to save superdict holding VNA trace for chip at port
    """

    # --- Initialise data acquisition ---
    data_path = portpath
    raw_data_folder = '\\Raw_data\\'

    # -- Get cold witch port number from portpath
    port = portpath.split('_')[-1]

    # Initialise required instruments
    vna = qt.instruments.get('vna')

    # -- Superdict --
    superdict = {}
    # VNA trace data
    superdict['Port'] = port
    superdict['Frequency (Hz)'] = []
    superdict['Phase (rad)'] = []
    superdict['Trace'] = []
    # Phase gradient data
    superdict['Phase unwrapped (rad)'] = []
    superdict['Phase gradient (rad/Hz)'] = []
    try:

        # --- VNA parameters ---
        settings = netw.setoutrange()
        netw.setbackrange(settings)

        span = fmax - fmin
        centerfreq = fmin + np.round(span / 2)
        rbw = resolution
        nop = points * span / rbw
        subints = 1
        if nop > max_nop:  # nop exceeds user maximum so we break span into subintervals
            subints = np.ceil(nop / max_nop)
            span = span / subints
            nop = max_nop

            if docomment:
                print('>>> Calculated nop exceeds max_nop:')
                print('>>> Span divided into ' + str(subints) + ' subintervals.')
                print('>>> nop set to max_nop = ' + str(max_nop))
        else:
            if docomment: print('>>> Calculated nop is: ' + str(nop))

        vna.set_power(vna_power)
        vna.set_span(span)
        vna.set_nop(nop)
        vna.set_bandwidth(rbw)
        fdelta = span / (nop - 1)
        art = 2 # choose artist for vna trace

        # --- Take trace ---

        fstart = fmin
        fstop = fmin + span
        vna.set_startfreq(fstart)
        vna.set_stopfreq(fstop)
        vna.edelay_auto()
        if docomment:print('>>> Taking VNA trace')
        if docomment:print('>>> Interval 1: fstart=' + str(fstart*1e-9) + 'GHz, fstop=' + str(fstop*1e-9) + 'GHz')
        freqs, trace = netw.trace(measure=1, get_result=1,make_plot=doplot, artist=2,filepath = data_path + raw_data_folder + 'vna_traces' + '/vna_trace_0' + '/vna_trace.dat')
        freqs *= 1e9
        # -- Gradient data
        phases = np.angle(trace)
        phases_unwrap = np.unwrap(phases)
        phases_unwrap_total = np.array(phases_unwrap)
        grads = np.abs(np.gradient(phases_unwrap, fdelta))

        if subints > 1: # multiple traces over subintervals

            for i in np.arange(1, int(subints)):

                # parameters required to correct for phase change between successive VNA traces
                phu_last = phases_unwrap_total[-1]

                fstart = fmin + i * span
                fstop = fstart + span
                if docomment:print('>>> Interval ' + str(i+1) + ': fstart=' + str(fstart*1e-9) + 'GHz, fstop=' + str(fstop*1e-9) + 'GHz')
                vna.set_startfreq(fstart)
                vna.set_stopfreq(fstop)
                vna.edelay_auto()
                fs, t = netw.trace(measure=1, get_result=1,make_plot=doplot, artist=2, filepath = data_path + raw_data_folder + 'vna_traces' + '/vna_trace_' + str(i) + '/vna_trace.dat')
                fs *= 1e9

                phases = np.angle(t)
                phases_unwrap = np.unwrap(phases)
                phases_unwrap_shifted = np.array(phases_unwrap) + (phu_last - phases_unwrap[0])
                phases_unwrap_total = np.append(phases_unwrap_total, phases_unwrap_shifted)

                freqs = np.append(freqs, fs)
                trace = np.append(trace, t)

                grads = np.append(grads, np.abs(np.gradient(phases_unwrap, fdelta)))
    except Exception as E:
        raise E
    finally:
        # -- Put VNA back to where it was
        if outrange: netw.setbackrange(settings)

        # --- Update dictionary ---
        superdict['Frequency (Hz)'] = np.array(freqs)
        superdict['Phase (rad)'] = np.array(phases)
        superdict['Trace'] = np.array(trace)
        superdict['Phase unwrapped (rad)'] = np.array(phases_unwrap)
        superdict['Phase gradient (rad/Hz)'] = np.array(grads)
        # --- Save dictionary ---
        np.save(data_path + '/superdict.npy', np.array(superdict))

        # -- Plot amplitude and phase trace
        amps = np.array(10 * np.log10(np.abs(trace) ** 2))

        if doplot:
            figname = 'VNA trace [fmin, fmax]='+str([fmin,fmax])
            fig = plt.figure(figname, figsize=(20,15))
            ax1 = fig.add_subplot(3, 1, 1)
            ax1.plot(freqs, amps)
            ax1.set_title('VNA amplitude and phase trace')
            ax1.set_ylabel(r'$10 \log(|S_{12}^2|)$ (dBm)')
            ax1.set_xlabel('Frequency (Hz)')
            ax1.grid(linestyle='--')

            ax2 = fig.add_subplot(3, 1, 3)
            ax2.plot(freqs, np.angle(trace))
            ax2.set_ylabel(r'Phase mod$(2\pi)$ (rad)')
            ax1.set_xlabel('Frequency (Hz)')

            ax3 = fig.add_subplot(3, 1, 3)
            ax2.plot(freqs, phases_unwrap_total)
            ax2.set_ylabel(r'Phase unwrapped (rad)$')
            ax1.set_xlabel('Frequency (Hz)')

            plt.show(block=0)
            ppl.savefigure(figname=figname, filepath=data_path)

        # -- Return data
        return superdict

def find_peaks(portpath='', freqs=[], grads=[], load=False, orig_sig=True, dist_peaks= 10e6,
               svw = 101, svp = 3, winlen = 1e6, freq_slice=10e6, stdv = 1, doplot=True):
    """
        Input:
            freqs:  array containing frequencies
            grads: array containing corresponding gradients
            port (str): port number of cold-switch corresponding to the loaded data
            portpath (str):   path to save and/or load gradient data, for chip at port, to and/or from. Used in conjunction with option load
        Options:
            orig_sig (boolean): Whether to show original signal and detect peaks on it. Defaults to True
            load (boolean): Load data from input portpath. Defaults to False

        Filtering with Savitzky-Golay:
            svw (int):  window size of filter. Must be odd. Defualts to 101
            svp (int):  order of convolution polynomial for SavGol filter. Defaults to 3

        Peak detection:
            dist_peaks: minimum distance between resonances. Should be known from simulations.
                        Defaults to 10Mhz
            winlen: Length of window, in Hz, which is used to calculate a peaks prominence.
                    Defaults to 1MHz
            freq_slice: size, in Hz, of slices into which signal is broken. Defaults to 10MHz
            Adaptive height and prominence calculation:
                stdv (int): number of standard deviations to add to average of signal in a given slice.
                            Defaults to 1
        """
    # -- Path for saving data
    peak_path = portpath + '/Peak_data'

    if not os.path.exists(peak_path):
        os.mkdir(peak_path)
    # -- Get cold witch port number from portpath
    port = portpath.split('_')[-1]

    # -- Dictionary for peak positions
    peakdict = {}
    peakdict['Port'] = port
    peakdict['Frequency (Hz)'] = []
    peakdict['Phase gradient (rad/Hz)'] = []
    peakdict['Phase gradient filt'] = []
    peakdict['Peak indexes orig'] = []
    peakdict['Peak indexes filt'] = []
    peakdict['Heights orig'] = []
    peakdict['Heights filt'] = []
    peakdict['Peak freqs orig'] = []
    peakdict['Peak freqs filt'] = []
    peakdict['Peak grads orig'] = []
    peakdict['Peak grads filt'] = []

    try:
        # -- Load data
        if load:
            print('Loading superdict')
            loaddict = np.load(portpath + '/superdict.npy').item()#, encoding='latin1').item()#
            freqs = np.array(loaddict['Frequency (Hz)'])
            grads = np.array(loaddict['Phase gradient (rad/Hz)'])

        peakdict['Frequency (Hz)'] = freqs
        peakdict['Phase gradient (rad/Hz)'] = grads

        # -- Filtering: Sav-Gol
        fdelta = (freqs[-1] - freqs[0])/(len(freqs)-1) # freqeuncy spacing of points
        grads_filt = sig.savgol_filter(grads, svw, svp)
        grads_filt = grads_filt/max(grads_filt) # Normalise to max gradient
        peakdict['Phase gradient filt'] = grads_filt

        # -- Peak detection
        # Slice up the data for adaptive height and prominence calculation
        slices = np.ceil((freqs[-1] - freqs[0])/freq_slice) # number of slices
        nop_slices = int(np.floor(len(grads_filt)/slices)) # number of samples in slice
        height_slices = [np.ones_like(freqs[i:i+nop_slices]) for i in range(0, len(freqs), nop_slices)]
        grads_slices = [grads[i:i+nop_slices] for i in range(0, len(grads), nop_slices)]
        grads_slices_filt = [grads_filt[i:i+nop_slices] for i in range(0, len(grads_filt), nop_slices)]

        # Calculate number of samples in frequency intervals
        dist_points = round(dist_peaks / fdelta)
        winlength = round(winlen/fdelta)

        # -- Unfiltered signal
        if orig_sig:
            for i, slicy in enumerate(grads_slices):# adaptive value used for height and prominence
                height = (np.mean(slicy) + stdv * np.std(slicy))
                height_slices[i] = height_slices[i] * height

            heights_orig = np.array([item for slice in height_slices for item in slice])
            peaks_orig, _ = sig.find_peaks(grads, wlen=winlength, height=heights_orig,
                                           distance=dist_points, prominence=heights_orig)
            proms = sig.peak_prominences(grads, peaks_orig)
            contour_heights_grads = grads[peaks_orig] - proms

            peakdict['Peak indexes orig'] = np.array(peaks_orig)
            peakdict['Heights orig'] = heights_orig
            peakdict['Peak freqs orig'] = [freqs[index] for index in peaks_orig]
            peakdict['Peak grads orig'] = [grads[index] for index in peaks_orig]

        # -- Filtered signal
        # reset height slices
        height_slices = [np.ones_like(freqs[i:i+nop_slices]) for i in range(0, len(freqs), nop_slices)]

        for i, slicy in enumerate(grads_slices_filt):
            height = (np.mean(slicy) + stdv * np.std(slicy))
            height_slices[i] = height_slices[i] * height

        heights_filt = np.array([item for slice in height_slices for item in slice])
        peaks_filt, _ = sig.find_peaks(grads_filt, wlen=winlength, height=heights_filt,
                                       distance=dist_points, prominence=heights_filt)
        proms_filt = sig.peak_prominences(grads_filt, peaks_filt)
        contour_heights_grads_filt = grads_filt[peaks_filt] - proms_filt

        peakdict['Peak indexes filt'] = np.array(peaks_filt)
        peakdict['Heights filt'] = heights_filt
        peakdict['Peak freqs filt'] = [freqs[index] for index in peaks_filt]
        peakdict['Peak grads filt'] = [grads_filt[index] for index in peaks_filt]
        # CHANGE THE ABOVE TO RETURN ORIGINAL GRADIENT

        # -- Plot
        r = 1
        c = 1
        if orig_sig:
            c = 2  # Add subfigure

        if doplot:
            figname = 'peaks_at_port_' + port
            fig = plt.figure(figname, figsize=(20, 5))

            fig.add_subplot(r, c, 1)
            plt.plot(freqs, grads_filt, label = 'Filtered signal')
            plt.plot(freqs, heights_filt, '--k', label = 'Adaptive height and prominence')
            plt.plot(freqs[peaks_filt], grads_filt[peaks_filt], "x", label = 'Peaks: ' + str(len(peaks_filt)))
            plt.vlines(x=freqs[peaks_filt], ymin=contour_heights_grads_filt, ymax=grads_filt[peaks_filt])
            plt.xlabel('Frequency (Hz)')
            plt.ylabel('Normalised gradient')
            plt.title('Gradient filtered with Savitsky-Golay;\n window='+str(svw)+', polynomial='+str(svp))
            plt.legend(loc='upper right')

            if orig_sig:
                fig.add_subplot(r, c, 2)
                plt.plot(freqs, grads, label = 'Original signal')
                plt.plot(freqs, heights_orig, '--k', label = 'Adaptive height and prominence')
                plt.plot(freqs[peaks_orig], grads[peaks_orig], "x", label = 'Peaks: ' + str(len(peaks_orig)))
                plt.vlines(x=freqs[peaks_orig], ymin=contour_heights_grads, ymax=grads[peaks_orig])
                plt.xlabel('Frequency (Hz)')
                plt.ylabel('Gradient (rad/Hz)')
                plt.title('Gradient of VNA phase')
                plt.legend(loc='upper right')

            # Save and show figure
            ppl.savefigure(figname = figname, filepath=peak_path)
            plt.show(block=0)

    finally:
        # Save peakdict
        np.save(portpath + '/peakdict.npy', np.array(peakdict))

        return peakdict
