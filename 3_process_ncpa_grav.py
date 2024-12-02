#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 30 17:32:57 2023

@author: pourren
"""

import glob
from astropy.io import fits
import argparse
import numpy as np
from scipy import signal as sig
from PySide2 import QtWidgets
from matplotlib import pyplot as plt
from matplotlib import patches
import time
import subprocess
from datetime import datetime

import os
import vlti

# =============================================================================
# Launch on ISS
# =============================================================================
# =============================================================================
# FUNCTIONS
# =============================================================================
def extract_ncpa_grav(cube_unbiased, nZ, nRtcMod, nRtcPause, modAmp):
    std_cube = cube_unbiased[:].std(axis=0)
    x = np.argmax(std_cube)
    x = np.unravel_index(x,std_cube.shape)
    flux = np.sum(cube_unbiased[:, :, x[1]-2:x[1]+3],axis=(1,2))
    flux = np.array(flux)
    t = np.arange(flux.shape[-1])
    
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

    mix_f = mix_f - np.median(mix_f[-100:])
    
    # Detect noise level on the last 100 samples
    m_a_d = lambda x: np.median(np.abs(x - np.median(x)))
    mad = m_a_d(mix_f[-100:])
    threshold = 15.0 * 1.4826 * mad #corresponds to 15 sigma over noise rms
    
    #Extract individual modulations
    iStartArr = []
    iStopArr = []
    nMeasureArr = []
    nPauseArr = []
    
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
    ncpabs =np.abs(ncpa-np.median(ncpa))
#%% remove oulayers
    for i in range(2):
        idex = np.argmax(ncpabs)
        ncpa = np.delete(ncpa,idex)
        ncpabs = np.delete(ncpabs,idex)
    return ncpa, iStart, iStop, nMeasure, nPause, threshold, nSample, mix_f

# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process NCPA files")
    parser.add_argument('noll', type=int, help="noll index of the modulation ")
    parser.add_argument('repeat', type=int, help="number of repetition for the modulation ")
    parser.add_argument('floop', type=int , help="AO loop frequency")
    parser.add_argument('name_acquisition', type=str, help="name of the acquisition")
    parser.add_argument('--timepermode','-t',type=float,default=1.5, help='time permode (sec)')
    args = parser.parse_args()
    
    nZ = args.repeat  # Number of repetitions
    nRtcMod = args.timepermode * args.floop  # Number of RTC samples for one Zernike modulation
    nRtcPause = int(0.5* args.floop)  # Number of RTC samples for a pause between two modulations
    modAmp = 0.2 #µmrms
    temp_folder = "/vltuser/iss/temp_ncpa/" # for tmporary storage of IRIS/GRAV data
    
    # Transfer GRAV SC acquisition to ISS
    os.system("""FILE=$(ssh grav@wgv "ls -tp /data/GRAVITY/INS_ROOT/SYSTEM/DETDATA/{0}_DIT.fits | grep -m1 \"\""); scp grav@wgv:$FILE {1} """.format(args.name_acquisition, temp_folder))
    # Transfer lastest GRAV SC background to ISS
    os.system("""FILE=$(ssh grav@wgv "ls -tp /data/GRAVITY/INS_ROOT/SYSTEM/DETDATA/GravNcpa_*bckg*_DIT.fits | grep -m1 \"\""); scp grav@wgv:$FILE {0} """.format(temp_folder))

    filename = temp_folder + args.name_acquisition + '_DIT.fits'
    bckgname = sorted(glob.glob(temp_folder+'GravNcpa_*bckg*.fits'))
    print('Filename : '+filename)
    print('Bckgname : '+bckgname)

    #Read SC data cube
    cube = fits.getdata(filename, 0)
    bckg = fits.getdata(bckg_name).mean(0)
    cube_unbiased = cube - bckg

    ncpa, iStart, iStop, nMeasure, nPause, threshold, nSample, mix_f = extract_ncpa_grav(cube_unbiased, nZ, nRtcMod, nRtcPause, modAmp)

    np.save('{0}NCPA_{1}.npy'.format(temp_folder,args.name_acquisition), np.array([ncpa]))    

    # Plot NCPA
    fig, axarr = plt.subplots(1, 1, figsize=(8,6))
    axarr.plot(ncpa*1e3, '.-', label='({0:.0f} nmRMS)'.format(np.mean(ncpa)*1e3))
    axarr.set_xlabel('Repetition of Noll {0}'.format(args.noll))
    axarr.set_ylabel('NCPA [nmRMS]')
    axarr.set_title(filename)
    axarr.set_xlim(0, len(ncpa))
    axarr.set_ylim(-np.abs(np.min(ncpa*1e3))*1.1,np.abs(np.max(ncpa*1e3))*1.1)
    axarr.grid()
    axarr.legend()
    print("Average NCPA noll {0}  amplitude ({2:.0f} nmRMS)".format(args.noll, np.mean(ncpa)*1e3))
    plt.tight_layout()
    plt.show()

    #Plot amplitude of 1.f modulation
    fig, axarr = plt.subplots(1, 1, figsize=(8,6))
    for iZ in range(args.repeat):
        xStart = iStart+iZ*(nMeasure+nPause) + nPause*2
        xStop = iStart+iZ*(nMeasure+nPause) + nMeasure + nPause*2
        axarr.add_patch(patches.Rectangle((xStart,0), xStop-xStart, np.max(mix_f)/2, alpha=0.2, color='grey'))
        axarr.text((xStart+xStop)/2.0, np.max(mix_f)/2, 'Z{0}'.format(args.noll), va='top', ha='center')
    axarr.plot(mix_f)
    axarr.plot([0, nSample], [threshold, threshold], 'k', lw=0.5)
    axarr.set_ylabel('1F amplitude')
    axarr.set_ylim(bottom=0)
    axarr.set_xlabel('Samples')
    plt.tight_layout()
    plt.show()



