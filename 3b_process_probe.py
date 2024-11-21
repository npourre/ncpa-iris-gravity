#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 30 17:44:37 2023

@author: pourren
"""

import glob
from astropy.io import fits
import numpy as np
from scipy import signal as sig
from scipy import stats
from matplotlib import pyplot as plt
from matplotlib import patches
from datetime import datetime
import argparse
import os

# =============================================================================
# adapted from Julien Woillez NAOMI NCPA code
# =============================================================================

def cutIrisDet(img, telescope, verbose=True): #Florentin's function
    telescope = int(telescope)
    if verbose:
        print("Input image shape",np.shape(img))
        print("tel ",telescope)
    nframes, nx, ny = np.shape(img)
    if verbose:
        print("Nframes, nx, ny",nframes, nx, ny)
    onetel = nx/4;
    imout = img[:,int(onetel * (4-telescope)):int(onetel * (4-telescope+1)),:]
    if verbose:
        print("Shape of output image",np.shape(imout))
    return imout

def extract_ncpa_iris(cube_1ut, nZ, nRtcMod, nRtcPause, modAmp):
    flux = np.var(cube_1ut,axis=(1,2))
    flux = np.array(flux)
    
    # Measure modulation frequency 
    freq, psd = sig.welch(flux, nperseg=2**14)
    i_f = np.argmax(psd[100:]) #100 to skip the lowest frequencies
    i_f+=100
    i_ff = np.argmax(psd[2*i_f-i_f//2:2*i_f+i_f//2])
    ff = freq[i_ff+2*i_f-i_f//2]
    f = ff/2.0

    #plt.figure()
    #plt.plot(psd)
    #plt.show()
    
    #Mix and filter to extract 1F modulation amplitude
    t = np.arange(flux.shape[-1])
    mix_f = flux*np.exp(1j*2*np.pi*f*t)
    mix_f = np.abs(sig.filtfilt(*sig.butter(4, f/2, 'lowpass'), mix_f))
    mix_f = mix_f[500:-500] # might cause problems
    nSample = mix_f.shape[0]

    mix_f = mix_f - np.median(mix_f)
    
    #Mix and filter to extract 2F modulation amplitude
    mix_2f = flux*np.exp(1j*2*np.pi*2*f*t)
    mix_2f = np.abs(sig.filtfilt(*sig.butter(4, f/2, 'lowpass'), mix_2f))
    mix_2f = mix_2f[500:-500] # might cause problems
    
    # Detect noise level on the last 1000 samples
    #mad = stats.median_abs_deviation(mix_f[-1000:])
    m_a_d = lambda x: np.median(np.abs(x - np.median(x)))
    mad = m_a_d(mix_f[-1000:])
    #threshold = 4*mix_f[-1000:].max()
    threshold = 20.0 * 1.4826 * mad
    
    # Find beginning and end of modulation
    iStart, iStop = np.where(mix_f > threshold)[0][[0, -1]]
    # Compute sample count for a measurement and a pause
    nMeasure = (iStop-iStart) * nRtcMod / ((nRtcMod+nRtcPause)*nZ+3*nRtcPause)
    nPause = (iStop-iStart) * nRtcPause / ((nRtcMod+nRtcPause)*nZ+3*nRtcPause)

    # Compute NCPA
    ncpa = []
    for iZ in range(nZ):
        # Extract 1.f modulation amplitude for current Zernike
        measure = mix_f[int(iStart+2*nPause+iZ*(nMeasure+nPause)):int(iStart+2*nPause+nMeasure+iZ*(nMeasure+nPause))]
        # Extract intervals where the three central minima are expected
        n = int(len(measure)/8+0.5)
        a = measure[1*n:3*n]
        b = measure[3*n:5*n]
        c = measure[5*n:7*n]
        # Determine the location of the minima
        iA = np.argmin(a)
        iB = np.argmin(b)+2*n
        iC = np.argmin(c)+4*n
        # Deduce the period of the slow modulation
        nPeriod = iC-iA
        # Convert phase between two consecutive minima into NCPA
        phase = np.pi*(iB-iA)/nPeriod
        ncpa.append(np.cos(phase)*modAmp)
    ncpa = np.array(ncpa)
    return ncpa, iStart, iStop, nMeasure, nPause, threshold, nSample, mix_f

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process NCPA files")
    parser.add_argument('tel', type=int, choices=range(5), help="Telescope index; use 0 for all four at once.")
    parser.add_argument('noll', type=int, help="noll index of the modulation for individual modes")
    parser.add_argument('timepermode',type=float,default=4., help='time permode (sec)')
    parser.add_argument('amplitude_slow',type=float,default=0.2, help='Amplitude of the slow modulation ramp [µm]')
    parser.add_argument('repeat', type=int, help="number of repetition for the modulation ")
    parser.add_argument('floop', type=int , help="AO loop frequency")
    args = parser.parse_args()
    
    os.system('rm /vltuser/aral/npourre/outdat*')
    #Parameters (same as modulation)
    nZ = args.repeat  # Number of repetitions
    nRtcMod = args.timepermode * args.floop  # Number of RTC samples for one Zernike modulation
    nRtcPause = int(0.5* args.floop)  # Number of RTC samples for a pause between two modulations
    modAmp = args.amplitude_slow
    
    #Read IRIS data cube
    filename = sorted(glob.glob(os.environ['INS_ROOT']+'/SYSTEM/DETDATA/IrisNcpa_*noll*.fits'))[-1]
    bckgname = sorted(glob.glob(os.environ['INS_ROOT']+'/SYSTEM/DETDATA/IrisNcpa_*bckg*.fits'))[-1]
    print('Filename : '+filename)
    print('Bckgname : '+bckgname)
    cube = fits.getdata(filename, 0)
    bckg = fits.getdata(bckgname, 0).mean(0)
    tStart = os.path.basename(filename).split("_")[1]
    cube = cube - bckg
    
    ncpa_tot = [] #ncpa measurements
    iStart_tot = []
    iStop_tot = []
    nMeasure_tot = []
    nPause_tot = []
    threshold_tot = []
    nSample_tot = []
    mix_f_tot = []
    if args.tel==0: # ALL 4 UTs
        for iTel in range(1,5):
            cube_1ut = cutIrisDet(cube, iTel)
            ncpa, iStart, iStop, nMeasure, nPause, threshold, nSample, mix_f = extract_ncpa_iris(cube_1ut, nZ, nRtcMod, nRtcPause, modAmp)
            ncpa_tot.append(np.copy(ncpa))
            iStart_tot.append(iStart)
            iStop_tot.append(iStop)
            nMeasure_tot.append(nMeasure)
            nPause_tot.append(nPause)
            threshold_tot.append(threshold)
            nSample_tot.append(nSample)
            mix_f_tot.append(np.copy(mix_f))
    elif args.tel in [1,2,3,4]: #one UT measurement
        cube_1ut = cutIrisDet(cube, args.tel)
        ncpa, iStart, iStop, nMeasure, nPause, threshold, nSample, mix_f = extract_ncpa_iris(cube_1ut, nZ, nRtcMod, nRtcPause, modAmp)
        ncpa_tot.append(np.copy(ncpa))
        iStart_tot.append(iStart)
        iStop_tot.append(iStop)
        nMeasure_tot.append(nMeasure)
        nPause_tot.append(nPause)
        threshold_tot.append(threshold)
        nSample_tot.append(nSample)
        mix_f_tot.append(np.copy(mix_f))
    else:
        print("WRONG TELESCOPE NUMBER")

    ncpa_tot = np.array(ncpa_tot) 
    iStart_tot = np.array(iStart_tot) 
    iStop_tot = np.array(iStop_tot) 
    nMeasure_tot = np.array(nMeasure_tot) 
    nPause_tot = np.array(nPause_tot) 
    threshold_tot = np.array(threshold_tot) 
    nSample_tot = np.array(nSample_tot) 
    mix_f_tot = np.array(mix_f_tot)

    np.save('/vltuser/aral/npourre/NCPA_{0}.npy'.format(tStart), ncpa_tot)
    np.save('/vltuser/aral/npourre/outdat1.npy',np.array([iStart_tot,iStop_tot, nMeasure_tot,nPause_tot]))
    np.save('/vltuser/aral/npourre/outdat2.npy',np.array([threshold_tot,nSample_tot]))
    np.save('/vltuser/aral/npourre/outdat3.npy',mix_f_tot)
    np.save('/vltuser/aral/npourre/outdat4.npy',filename)
