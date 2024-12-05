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

def download_latest_file(server, remote_dir, name, local_dir):
    # Construct the command to find the latest file with the given prefix
    find_command = (
        f"""FILE=$(ssh {server} "ls -tp {remote_dir}/{name} 2>/dev/null | head -n 1"); """
        f"""if [ -n "$FILE" ]; then scp {server}:$FILE {local_dir}; """
        f"""else echo 'No files found with the name {name}'; fi"""
    )
    
    # Execute the command
    result = os.system(find_command)
    
    if result == 0:
        print("File downloaded successfully.")
    else:
        print("An error occurred during the download.")

def extract_ncpa_iris_PAR(cube_1ut, nZ, nRtcMod, nRtcPause, modAmp, repeat):
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
    iter_length = int((iStop - iStart)/repeat)
    nMeasure = (iter_length) * nRtcMod / ((nRtcMod+nRtcPause)*nZ+3*nRtcPause)
    nPause = (iter_length) * nRtcPause / ((nRtcMod+nRtcPause)*nZ+3*nRtcPause)

    # Compute NCPA
    ncpas = []
    for iR in range(repeat):
        ncpa = []
        for iZ in range(nZ):
            # Extract 1.f modulation amplitude for current Zernike
            measure = mix_f[int(iStart+iR*iter_length+2*nPause+iZ*(nMeasure+nPause)):int(iStart+iR*iter_length+2*nPause+nMeasure+iZ*(nMeasure+nPause))]
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
        ncpas.append(np.copy(ncpa))
    ncpas = np.array(ncpas)
    return ncpas, iStart, iStop, nMeasure, nPause, threshold, nSample, mix_f

def extract_ncpa_iris_SEQ(cube_1ut, nZ, nRtcMod, nRtcPause, modAmp, repeat):
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

def D_process_ncpa_iris(tel, mode_start, mode_end, repeat, floop, name_acquisition, timepermode, silent, temp_folder, sequence):
    if tel==0: #all UTs measurements
       telescopes = [1,2,3,4]
       ut_str = "1234"
    elif tel in [1,2,3,4]: #one UT measurement
        telescopes = [tel]
        ut_str = str(tel)
    else:
        print("WRONG TELESCOPE NUMBER")


    #Parameters (same as modulation)
    if sequence == 'PAR':
        iZs = np.arange(mode_start, mode_end+1)
        nZ = len(iZs)  # Number of modes
    elif sequence == 'SEQ':
        nZ = repeat
        noll = mode_start
    nRtcMod = timepermode * floop  # Number of RTC samples for one Zernike modulation
    nRtcPause = int(0.5* floop)  # Number of RTC samples for a pause between two modulations
    modAmp = 0.2 #µmrms

    # Transfer Iris acquisition to ISS
    server = "aral@waral"
    remote_dir = "/data/ARAL/INS_ROOT/SYSTEM/DETDATA" 
    # Transfer lastest Iris background to ISS
    download_latest_file(server, remote_dir, "IrisNcpa_*bckg*_DIT.fits", temp_folder)
    filename = name_acquisition + '_DIT.fits'
    filename = temp_folder+filename
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
        if sequence == 'PAR':
            ncpas, iStart, iStop, nMeasure, nPause, threshold, nSample, mix_f = extract_ncpa_iris_PAR(cube_1ut, nZ, nRtcMod, nRtcPause, modAmp,repeat)
        elif sequence == 'SEQ':
            ncpas, iStart, iStop, nMeasure, nPause, threshold, nSample, mix_f = extract_ncpa_iris_SEQ(cube_1ut, nZ, nRtcMod, nRtcPause, modAmp,repeat)
        ncpa_tot.append(np.copy(ncpas))
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

    np.save('{0}NCPA_{1}.npy'.format(temp_folder,name_acquisition), ncpa_tot)

    if silent==0:
        # Plot NCPA
        if sequence == 'PAR':
            if tel==0 and ncpa_tot.shape[0]==4: #4 UTs at once
                fig, axarr = plt.subplots(2, 2, figsize=(12,8))
                for indTel in range(4):
                    for iui in range(ncpa_tot.shape[1]):
                        axarr.ravel()[indTel].plot(iZs, ncpa_tot[indTel][iui]*1e3, '.-')
                    axarr.ravel()[indTel].plot(iZs, ncpa_tot[indTel].mean(0)*1e3, '.-',lw=3,color='k',label="Average")
                    axarr.ravel()[indTel].set_xlabel('Noll number')
                    axarr.ravel()[indTel].set_ylabel('NCPA [nmRMS]')
                    axarr.ravel()[indTel].set_title('UT{0}'.format(indTel+1))
                    axarr.ravel()[indTel].set_ylim(-np.abs(np.min(ncpa_tot[indTel]*1e3))*1.1,np.abs(np.max(ncpa_tot[indTel]*1e3))*1.1)
                    axarr.ravel()[indTel].grid()
                    axarr.ravel()[indTel].legend()
                plt.suptitle(filename)
                plt.tight_layout()
                plt.show()
            elif (tel in [1,2,3,4]) and ncpa_tot.shape[0]==1: #one UT measurement
                fig, axarr = plt.subplots(1, 1, figsize=(8,6))
                for iui in range(ncpa_tot.shape[1]):
                    axarr.plot(iZs, ncpa_tot[0][iui]*1e3, '.-')
                axarr.plot(iZs, ncpa_tot[0].mean(0)*1e3, '.-',lw=3,color='k',label="Average")
                axarr.set_xlabel('Noll number')
                axarr.set_ylabel('NCPA [nmRMS]')
                axarr.set_title(filename)
                axarr.text(0,0,'UT{0}'.format(tel),fontsize=20)
                axarr.set_ylim(-np.abs(np.min(ncpa_tot[0]*1e3))*1.1,np.abs(np.max(ncpa_tot[0]*1e3))*1.1)
                axarr.grid()
                axarr.legend()
                plt.tight_layout()
                plt.show()
            else:
                print("WRONG TELESCOPE NUMBER")

            #Plot amplitude of 1.f modulation
            if tel==0: #4 UTs at once
                fig, axarr = plt.subplots(2, 2, figsize=(12,8))
                for indTel in range(4):
                    for iR in range(repeat):
                        for iZ in range(len(iZs)):
                            iter_length = int((iStopArr[indTel] - iStartArr[indTel])/repeat)
                            xStart = iStartArr[indTel]+iter_length*iR+iZ*(nMeasureArr[indTel]+nPauseArr[indTel]) + nPauseArr[indTel]*2
                            xStop = iStartArr[indTel]+iter_length*iR+iZ*(nMeasureArr[indTel]+nPauseArr[indTel]) + nPauseArr[indTel]*2 + nMeasureArr[indTel]
                            axarr.ravel()[indTel].add_patch(patches.Rectangle((xStart,0), xStop-xStart,  np.max(mix_f_Arr[indTel])/2, alpha=0.2, color='grey'))
                            axarr.ravel()[indTel].text((xStart+xStop)/2.0,  np.max(mix_f_Arr[indTel])/2, 'Z{0}'.format(iZs[iZ]), va='top', ha='center')
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
            elif tel in [1,2,3,4]: #one UT measurement
                fig, axarr = plt.subplots(1, 1, figsize=(8,6))
                iter_length = int((iStopArr[0] - iStartArr[0])/repeat)
                for iR in range(repeat):
                    for iZ in range(len(iZs)):
                        xStart = iStartArr[0]+iter_length*iR+iZ*(nMeasureArr[0]+nPauseArr[0]) + nPauseArr[0]*2
                        xStop = iStartArr[0]+iter_length*iR+iZ*(nMeasureArr[0]+nPauseArr[0]) + nMeasureArr[0] + nPauseArr[0]*2
                        axarr.add_patch(patches.Rectangle((xStart,0), xStop-xStart, np.max(mix_f_Arr[0])/2, alpha=0.2, color='grey'))
                        axarr.text((xStart+xStop)/2.0, np.max(mix_f_Arr[0])/2, 'Z{0}'.format(iZs[iZ]), va='top', ha='center')
                axarr.plot(mix_f_Arr[0])
                axarr.plot([0, nSample[0]], [threshold[0], threshold[0]], 'k', lw=0.5)
                axarr.set_ylabel('1F amplitude')
                axarr.set_title('UT{0}'.format(tel))
                axarr.legend()
                axarr.set_ylim(bottom=0)
                axarr.set_xlabel('Samples')
                plt.tight_layout()
                plt.show()
            else:
                print("WRONG TELESCOPE NUMBER")

        elif sequence == 'SEQ':
            if tel==0 and ncpa_tot.shape[0]==4: #4 UTs at once
                fig, axarr = plt.subplots(2, 2, figsize=(12,8))
                for indTel in range(4):
                    axarr.ravel()[indTel].plot(ncpa_tot[indTel]*1e3, '.-', label='({0:.0f} nmRMS)'.format(np.mean(ncpa_tot[indTel])*1e3))
                    axarr.ravel()[indTel].set_xlabel('Repetition of Noll {0}'.format(noll))
                    axarr.ravel()[indTel].set_ylabel('NCPA [nmRMS]')
                    axarr.ravel()[indTel].set_title('UT{0}'.format(indTel+1))
                    axarr.ravel()[indTel].set_xlim(0, len(ncpa_tot[indTel]))
                    axarr.ravel()[indTel].set_ylim(-np.abs(np.min(ncpa_tot[indTel]*1e3))*1.1,np.abs(np.max(ncpa_tot[indTel]*1e3))*1.1)
                    axarr.ravel()[indTel].grid()
                    axarr.ravel()[indTel].legend()
                    print("Average NCPA noll {0}  on UT {1} amplitude ({2:.0f} nmRMS)".format(noll, indTel+1, np.mean(ncpa_tot[indTel])*1e3))
                plt.suptitle(filename)
                plt.tight_layout()
                plt.show()
            elif (tel in [1,2,3,4]) and ncpa_tot.shape[0]==1: #one UT measurement
                fig, axarr = plt.subplots(1, 1, figsize=(8,6))
                axarr.plot(ncpa_tot[0]*1e3, '.-', label='({0:.0f} nmRMS)'.format(np.mean(ncpa_tot[0])*1e3))
                axarr.set_xlabel('Repetition of Noll {0}'.format(noll))
                axarr.set_ylabel('NCPA [nmRMS]')
                axarr.set_title(filename)
                axarr.text(0,0,'UT{0}'.format(tel),fontsize=20)
                axarr.set_xlim(0, len(ncpa_tot[0]))
                axarr.set_ylim(-np.abs(np.min(ncpa_tot[0]*1e3))*1.1,np.abs(np.max(ncpa_tot[0]*1e3))*1.1)
                axarr.grid()
                axarr.legend()
                print("Average NCPA noll {0}  on UT {1} amplitude ({2:.0f} nmRMS)".format(noll, tel, np.mean(ncpa_tot[0])*1e3))
                plt.tight_layout()
                plt.show()
            else:
                print("WRONG TELESCOPE NUMBER")

            #Plot amplitude of 1.f modulation
            if tel==0: #4 UTs at once
                fig, axarr = plt.subplots(2, 2, figsize=(12,8))
                for indTel in range(4):
                    for iZ in range(repeat):
                        xStart = iStartArr[indTel]+iZ*(nMeasureArr[indTel]+nPauseArr[indTel]) + nPauseArr[indTel]*2
                        xStop = iStartArr[indTel]+iZ*(nMeasureArr[indTel]+nPauseArr[indTel]) + nPauseArr[indTel]*2 + nMeasureArr[indTel]
                        axarr.ravel()[indTel].add_patch(patches.Rectangle((xStart,0), xStop-xStart,  np.max(mix_f_Arr[indTel])/2, alpha=0.2, color='grey'))
                        axarr.ravel()[indTel].text((xStart+xStop)/2.0,  np.max(mix_f_Arr[indTel])/2, 'Z{0}'.format(noll), va='top', ha='center')
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
            elif tel in [1,2,3,4]: #one UT measurement
                fig, axarr = plt.subplots(1, 1, figsize=(8,6))
                for iZ in range(repeat):
                    xStart = iStartArr[0]+iZ*(nMeasureArr[0]+nPauseArr[0]) + nPauseArr[0]*2
                    xStop = iStartArr[0]+iZ*(nMeasureArr[0]+nPauseArr[0]) + nMeasureArr[0] + nPauseArr[0]*2
                    axarr.add_patch(patches.Rectangle((xStart,0), xStop-xStart, np.max(mix_f_Arr[0])/2, alpha=0.2, color='grey'))
                    axarr.text((xStart+xStop)/2.0, np.max(mix_f_Arr[0])/2, 'Z{0}'.format(noll), va='top', ha='center')
                axarr.plot(mix_f_Arr[0])
                axarr.plot([0, nSample[0]], [threshold[0], threshold[0]], 'k', lw=0.5)
                axarr.set_ylabel('1F amplitude')
                axarr.set_title('UT{0}'.format(tel))
                axarr.legend()
                #axarr.set_xlim(0, np.max(iStartArr[0])+nMeasureArr[0]*14+nPauseArr[0]*11)
                axarr.set_ylim(bottom=0)
                axarr.set_xlabel('Samples')
                plt.tight_layout()
                plt.show()
            else:
                print("WRONG TELESCOPE NUMBER")


