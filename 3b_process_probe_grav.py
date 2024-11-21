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
from matplotlib import pyplot as plt
from matplotlib import patches
from datetime import datetime
import argparse
import os

# =============================================================================
# adapted from Julien Woillez NAOMI NCPA code
# =============================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process NCPA files")
    parser.add_argument('noll', type=int, help="noll index of the modulation for individual modes")
    parser.add_argument('timepermode',type=float,default=4., help='time permode (sec)')
    parser.add_argument('amplitude_slow',type=float,default=0.2, help='Amplitude of the slow modulation ramp [µm]')
    parser.add_argument('repeat', type=int, help="number of repetition for the modulation ")
    parser.add_argument('floop', type=int , help="AO loop frequency")
    args = parser.parse_args()
    
    os.system('rm /vltuser/grav/npourre/outdat*')
    #Parameters (same as modulation)
    nZ = args.repeat  # Number of repetitions
    nRtcMod = args.timepermode * args.floop  # Number of RTC samples for one Zernike modulation
    nRtcPause = args.floop  # Number of RTC samples for a pause between two modulations
    modAmp = args.amplitude_slow
    
    #Read SC data cube
    if args.noll==0:
        filename = sorted(glob.glob(os.environ['INS_ROOT']+'/SYSTEM/DETDATA/ncpa_acqal*_DIT.fits'))[-1]
    else:
        nols = str(args.noll)
        if len(nols)==1:
            nols = '0'+nols
        filename = sorted(glob.glob(os.environ['INS_ROOT']+'/SYSTEM/DETDATA/ncpa_acq1m{0}*_DIT.fits'.format(nols)))[-1]
    print('Filename : '+filename)
    cube = fits.getdata(filename, 0)
    bckg_name= sorted(glob.glob(os.environ['INS_ROOT']+'/SYSTEM/DETDATA/ncpa_bckg*_DIT.fits'))[-1]
    print('Filename bckg : '+bckg_name)
    bckg = fits.getdata(bckg_name).mean(0)
    cube_unbiased = cube - bckg
    
    tStart = filename[-28:-9]
    
    std_cube = cube_unbiased[:].std(axis=0)
    x = np.argmax(std_cube)
    x = np.unravel_index(x,std_cube.shape)
    flux = np.sum(cube_unbiased[:, :, x[1]-2:x[1]+3],axis=(1,2))
    flux = np.array(flux)
    t = np.arange(flux.shape[-1])
    np.save('/vltuser/grav/npourre/outdat4.npy',np.array([t,flux]))
    
    # Measure modulation frequency 
    freq, psd = sig.welch(flux, nperseg=2**14)
    i_f = np.argmax(psd[100:]) #100 to skip the lowest frequencies
    i_f+=100
    i_ff = np.argmax(psd[2*i_f-i_f//2:2*i_f+i_f//2])
    ff = freq[i_ff+2*i_f-i_f//2]
    f = ff/2.0
    
    #Mix and filter to extract 1F modulation amplitude
    mix_f = flux*np.exp(1j*2*np.pi*f*t)
    mix_f = np.abs(sig.filtfilt(*sig.butter(4, f/2, 'lowpass'), mix_f))
    mix_f = mix_f[500:-500] # might cause problems
    nSample = mix_f.shape[0]
    np.save('/vltuser/grav/npourre/outdat3.npy',mix_f)
    #Mix and filter to extract 2F modulation amplitude
    mix_2f = flux*np.exp(1j*2*np.pi*2*f*t)
    mix_2f = np.abs(sig.filtfilt(*sig.butter(4, f/2, 'lowpass'), mix_2f))
    mix_2f = mix_2f[500:-500] # might cause problems
    
    # Detect noise level on the last 1000 samples
    threshold = 2*mix_f[:100].max()
    
    #Extract individual modulations
    iStartArr = []
    iStopArr = []
    nMeasureArr = []
    nPauseArr = []
    
    # Find beginning and end of modulation
    iStart, iStop = np.where(mix_f > threshold)[0][[0, -1]]
    # Compute sample count for a measurement and a pause
    nMeasure = (iStop-iStart)/(nRtcMod*nZ+nRtcPause*(nZ-1))*nRtcMod
    nPause = (iStop-iStart)/(nRtcMod*nZ+nRtcPause*(nZ-1))*nRtcPause
    # Save interval parameters
    iStartArr.append(iStart)
    iStopArr.append(iStop)
    nMeasureArr.append(nMeasure)
    nPauseArr.append(nPause)
    # Compute NCPA
    ncpa = []
    for iZ in range(nZ):
        # Extract 1.f modulation amplitude for current Zernike
        measure = mix_f[iStart+int(iZ*(nMeasure+nPause)):iStart+int(iZ*(nMeasure+nPause)+nMeasure)]
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
    ncpabs =np.abs(ncpa-np.mean(ncpa))
#%% remove oulayers
    for i in range(2):
        idex = np.argmax(ncpabs)
        ncpa = np.delete(ncpa,idex)
        ncpabs = np.delete(ncpabs,idex)
    # Save NCPA modal offsets
    modal_offsets = np.zeros((1, 50), dtype=np.float32)
    modal_offsets[0, args.noll-2] = -np.mean(ncpa)  # Negative sign to remove the NCPA
    hdulist = fits.HDUList([fits.PrimaryHDU(modal_offsets)])
    hdulist.writeto('/vltuser/grav/npourre/NCPA_{0}.fits'.format(tStart), overwrite=True)
    
    np.save('/vltuser/grav/npourre/outdat1.npy',np.array([iStartArr,iStopArr, nMeasureArr,nPauseArr]))
    np.save('/vltuser/grav/npourre/outdat2.npy',np.array([threshold,nSample]))
    np.save('/vltuser/grav/npourre/outdat5.npy',np.array([freq,psd]))
    np.save('/vltuser/grav/npourre/outdat6.npy',mix_2f)
    np.save('/vltuser/grav/npourre/outdat7.npy',ncpa)
    np.save('/vltuser/grav/npourre/outdat8.npy',filename)
