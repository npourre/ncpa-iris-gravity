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
from scipy import stats
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
def cutIrisDet(img, telescope, verbose=False): #Florentin's function
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
    
    #Mix and filter to extract 1F modulation amplitude
    t = np.arange(flux.shape[-1])
    mix_f = flux*np.exp(1j*2*np.pi*f*t)
    mix_f = np.abs(sig.filtfilt(*sig.butter(4, f/2, 'lowpass'), mix_f))
    mix_f = mix_f[500:-500] # might cause problems
    nSample = mix_f.shape[0]

    mix_f = mix_f - np.median(mix_f[-1000:])
    
    #Mix and filter to extract 2F modulation amplitude
    mix_2f = flux*np.exp(1j*2*np.pi*2*f*t)
    mix_2f = np.abs(sig.filtfilt(*sig.butter(4, f/2, 'lowpass'), mix_2f))
    mix_2f = mix_2f[500:-500] # might cause problems
    
    # Detect noise level on the last 1000 samples
    m_a_d = lambda x: np.median(np.abs(x - np.median(x)))
    mad = m_a_d(mix_f[-1000:])
    threshold = 20.0 * 1.4826 * mad #corresponds to 20 sigma over noise rms
    
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

# =============================================================================
# MAIN
# =============================================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process NCPA files")
    parser.add_argument('tel', type=int, choices=range(5), help="Telescope index; use 0 for all four at once.")
    parser.add_argument('noll', type=int, help="noll index of the modulation ")
    parser.add_argument('repeat', type=int, help="number of repetition for the modulation ")
    parser.add_argument('floop', type=int , help="AO loop frequency")
    parser.add_argument('name_acquisition', type=str, help="name of the acquisition")
    parser.add_argument('--timepermode','-t',type=float,default=1.5, help='time permode (sec)')
    args = parser.parse_args()
    
    if args.tel==0: #all UTs measurements
       telescopes = [1,2,3,4]
       ut_str = "1234"
    elif args.tel in [1,2,3,4]: #one UT measurement
        telescopes = [args.tel]
        ut_str = str(args.tel)
    else:
        print("WRONG TELESCOPE NUMBER")

    #Parameters (same as modulation)
    nZ = args.repeat  # Number of repetitions
    nRtcMod = args.timepermode * args.floop  # Number of RTC samples for one Zernike modulation
    nRtcPause = int(0.5* args.floop)  # Number of RTC samples for a pause between two modulations
    modAmp = 0.2 #µmrms
    temp_folder = "/vltuser/iss/temp_ncpa/" # for tmporary storage of IRIS/GRAV data

    # Transfer Iris acquisition to ISS
    os.system("""FILE=$(ssh aral@waral "ls -tp /data/ARAL/INS_ROOT/SYSTEM/DETDATA/{0}_DIT.fits | grep -m1 \"\""); scp aral@waral:$FILE {1} """.format(args.name_acquisition, temp_folder))
    # Transfer lastest Iris background to ISS
    os.system("""FILE=$(ssh aral@waral "ls -tp /data/ARAL/INS_ROOT/SYSTEM/DETDATA/IrisNcpa_*bckg*_DIT.fits | grep -m1 \"\""); scp aral@waral:$FILE {0} """.format(temp_folder))

    filename = temp_folder + args.name_acquisition + '_DIT.fits'
    bckgname = sorted(glob.glob(temp_folder+'IrisNcpa_*bckg*.fits'))[-1]
    print('Filename : '+filename)
    print('Bckgname : '+bckgname)

    #Read IRIS data cube
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
    for iTel in telescopes:
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

    ncpa_tot = np.array(ncpa_tot) 
    iStartArr = np.array(iStart_tot).astype(int)
    iStopArr = np.array(iStop_tot).astype(int)
    nMeasureArr = np.array(nMeasure_tot) 
    nPauseArr = np.array(nPause_tot) 
    threshold = np.array(threshold_tot) 
    nSample = np.array(nSample_tot) 
    mix_f_Arr = np.array(mix_f_tot)

    np.save('{0}NCPA_{1}.npy'.format(temp_folder,args.name_acquisition), ncpa_tot)

    # Plot NCPA
    if args.tel==0 and ncpaArr.shape[0]==4: #4 UTs at once
        fig, axarr = plt.subplots(2, 2, figsize=(12,8))
        for indTel in range(4):
            axarr.ravel()[indTel].plot(ncpaArr[indTel]*1e3, '.-', label='({0:.0f} nmRMS)'.format(np.mean(ncpaArr[indTel])*1e3))
            axarr.ravel()[indTel].set_xlabel('Repetition of Noll {0}'.format(args.noll))
            axarr.ravel()[indTel].set_ylabel('NCPA [nmRMS]')
            axarr.ravel()[indTel].set_title('UT{0}'.format(indTel+1))
            axarr.ravel()[indTel].set_xlim(0, len(ncpaArr[indTel]))
            axarr.ravel()[indTel].set_ylim(-np.abs(np.min(ncpaArr[indTel]*1e3))*1.1,np.abs(np.max(ncpaArr[indTel]*1e3))*1.1)
            axarr.ravel()[indTel].grid()
            axarr.ravel()[indTel].legend()
            print("Average NCPA noll {0}  on UT {1} amplitude ({2:.0f} nmRMS)".format(args.noll, indTel+1, np.mean(ncpaArr[indTel])*1e3))
        plt.suptitle(filename)
        plt.tight_layout()
        plt.show()
    elif (args.tel in [1,2,3,4]) and ncpaArr.shape[0]==1: #one UT measurement
        fig, axarr = plt.subplots(1, 1, figsize=(8,6))
        axarr.plot(ncpaArr[0]*1e3, '.-', label='({0:.0f} nmRMS)'.format(np.mean(ncpaArr[0])*1e3))
        axarr.set_xlabel('Repetition of Noll {0}'.format(args.noll))
        axarr.set_ylabel('NCPA [nmRMS]')
        axarr.set_title(filename)
        axarr.text(0,0,'UT{0}'.format(args.tel),fontsize=20)
        axarr.set_xlim(0, len(ncpaArr[0]))
        axarr.set_ylim(-np.abs(np.min(ncpaArr[0]*1e3))*1.1,np.abs(np.max(ncpaArr[0]*1e3))*1.1)
        axarr.grid()
        axarr.legend()
        print("Average NCPA noll {0}  on UT {1} amplitude ({2:.0f} nmRMS)".format(args.noll, args.tel, np.mean(ncpaArr[0])*1e3))
        plt.tight_layout()
        plt.show()
    else:
        print("WRONG TELESCOPE NUMBER")

    #Plot amplitude of 1.f modulation
    if args.tel==0: #4 UTs at once
        fig, axarr = plt.subplots(2, 2, figsize=(12,8))
        for indTel in range(4):
            for iZ in range(args.repeat):
                xStart = iStartArr[indTel]+iZ*(nMeasureArr[indTel]+nPauseArr[indTel]) + nPauseArr[indTel]*2
                xStop = iStartArr[indTel]+iZ*(nMeasureArr[indTel]+nPauseArr[indTel]) + nPauseArr[indTel]*2 + nMeasureArr[indTel]
                axarr.ravel()[indTel].add_patch(patches.Rectangle((xStart,0), xStop-xStart,  np.max(mix_f_Arr[indTel])/2, alpha=0.2, color='grey'))
                axarr.ravel()[indTel].text((xStart+xStop)/2.0,  np.max(mix_f_Arr[indTel])/2, 'Z{0}'.format(args.noll), va='top', ha='center')
            axarr.ravel()[indTel].plot(mix_f_Arr[indTel])
            axarr.ravel()[indTel].plot([0, nSample[indTel]], [threshold[indTel], threshold[indTel]], 'k', lw=0.5)
            axarr.ravel()[indTel].set_ylabel('1F amplitude')
            axarr.ravel()[indTel].set_title('UT{0}'.format(indTel+1))
            axarr.ravel()[indTel].legend()
            #axarr.ravel()[indTel].set_xlim(0, np.max(iStartArr[indTel])+nMeasureArr[indTel]*14+nPauseArr[indTel]*11)
            axarr.ravel()[indTel].set_ylim(bottom=0)
            axarr.ravel()[indTel].set_xlabel('Samples')
        plt.suptitle(filename)
        plt.tight_layout()
        plt.show()
    elif args.tel in [1,2,3,4]: #one UT measurement
        fig, axarr = plt.subplots(1, 1, figsize=(8,6))
        for iZ in range(args.repeat):
            xStart = iStartArr[0]+iZ*(nMeasureArr[0]+nPauseArr[0]) + nPauseArr[0]*2
            xStop = iStartArr[0]+iZ*(nMeasureArr[0]+nPauseArr[0]) + nMeasureArr[0] + nPauseArr[0]*2
            axarr.add_patch(patches.Rectangle((xStart,0), xStop-xStart, np.max(mix_f_Arr[0])/2, alpha=0.2, color='grey'))
            axarr.text((xStart+xStop)/2.0, np.max(mix_f_Arr[0])/2, 'Z{0}'.format(args.noll), va='top', ha='center')
        axarr.plot(mix_f_Arr[0])
        axarr.plot([0, nSample[0]], [threshold[0], threshold[0]], 'k', lw=0.5)
        axarr.set_ylabel('1F amplitude')
        axarr.set_title('UT{0}'.format(args.tel))
        axarr.legend()
        #axarr.set_xlim(0, np.max(iStartArr[0])+nMeasureArr[0]*14+nPauseArr[0]*11)
        axarr.set_ylim(bottom=0)
        axarr.set_xlabel('Samples')
        plt.tight_layout()
        plt.show()
    else:
        print("WRONG TELESCOPE NUMBER")
    


