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
# FUNCTIONS
# =============================================================================

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

def extract_ncpa_grav_PAR(cube_unbiased, nZ, nRtcMod, nRtcPause, modAmp, repeat):
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

    #Mix and filter to extract 2F modulation amplitude
    mix_2f = flux*np.exp(1j*2*np.pi*2*f*t)
    mix_2f = np.abs(sig.filtfilt(*sig.butter(4, f/2, 'lowpass'), mix_2f))
    mix_2f = mix_2f[500:-500] # might cause problems

    mix_f = mix_f - np.median(mix_f[-500:])
    
    # Detect noise level on the last 100 samples
    m_a_d = lambda x: np.median(np.abs(x - np.median(x)))
    mad = m_a_d(mix_f[-100:])
    threshold = 20.0 * 1.4826 * mad #corresponds to 15 sigma over noise rms
    

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


def extract_ncpa_grav_SEQ(cube_unbiased, nZ, nRtcMod, nRtcPause, modAmp, repeat):
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

def D_process_ncpa_grav(mode_start, mode_end, repeat, floop, name_acquisition, timepermode, silent, temp_folder, sequence):
    if sequence == 'PAR':
        iZs = np.arange(mode_start, mode_end+1)
        nZ = len(iZs)  # Number of modes
    elif sequence == 'SEQ':
        nZ = repeat
        noll = mode_start
    nRtcMod = timepermode * floop  # Number of RTC samples for one Zernike modulation
    nRtcPause = int(0.5* floop)  # Number of RTC samples for a pause between two modulations
    modAmp = 0.2 #µmrms
    
    # Transfer GRAV SC acquisition to ISS
    # Transfer Iris acquisition to ISS
    server = "grav@wgv"
    remote_dir = "/data/GRAVITY/INS_ROOT/SYSTEM/DETDATA" 
    # Transfer lastest Iris background to ISS
    download_latest_file(server, remote_dir, "GravNcpa_*bckg*_DIT.fits", temp_folder)
    filename = name_acquisition + '_DIT.fits'
    filename = temp_folder+filename

    bckgname = sorted(glob.glob(temp_folder+'GravNcpa_*bckg*.fits'))
    print('Filename : '+filename)
    print('Bckgname : '+bckgname)

    #Read SC data cube
    cube = fits.getdata(filename, 0)
    bckg = fits.getdata(bckg_name).mean(0)
    cube_unbiased = cube - bckg

    if sequence == 'PAR':
        ncpa, iStart, iStop, nMeasure, nPause, threshold, nSample, mix_f = extract_ncpa_grav_PAR(cube_unbiased, nZ, nRtcMod, nRtcPause, modAmp,repeat)
    elif sequence == 'SEQ':
        ncpa, iStart, iStop, nMeasure, nPause, threshold, nSample, mix_f = extract_ncpa_grav_SEQ(cube_unbiased, nZ, nRtcMod, nRtcPause, modAmp,repeat)

    np.save('{0}NCPA_{1}.npy'.format(temp_folder,name_acquisition), np.array([ncpa]))    

    if silent==0:
        # Plot NCPA
        if sequence == 'PAR':
            # Plot NCPA
            fig, axarr = plt.subplots(1, 1, figsize=(8,6))
            for iui in range(ncpa.shape[0]):
                axarr.plot(iZs, ncpa[iui]*1e3, '.-')
            axarr.plot(iZs, ncpa.mean(0)*1e3, '.-',lw=3,color='k',label="Average")
            axarr.set_xlabel('Noll number')
            axarr.set_ylabel('NCPA [nmRMS]')
            axarr.set_title(filename)
            axarr.set_xlim(0, len(ncpa))
            axarr.set_ylim(-np.abs(np.min(ncpa*1e3))*1.1,np.abs(np.max(ncpa*1e3))*1.1)
            axarr.grid()
            axarr.legend()
            plt.tight_layout()
            plt.show()

            #Plot amplitude of 1.f modulation
            fig, axarr = plt.subplots(1, 1, figsize=(8,6))
            iter_length = int((iStop - iStart)/repeat)
            for iR in range(repeat):
                for iZ in range(repeat):
                    xStart = iStart+iter_length*iR+iZ*(nMeasure+nPause) + nPause*2
                    xStop = iStart+iter_length*iR+iZ*(nMeasure+nPause) + nMeasure + nPause*2
                    axarr.add_patch(patches.Rectangle((xStart,0), xStop-xStart, np.max(mix_f)/2, alpha=0.2, color='grey'))
                    axarr.text((xStart+xStop)/2.0, np.max(mix_f)/2, 'Z{0}'.format(iZs[iZ]), va='top', ha='center')
            axarr.plot(mix_f)
            axarr.plot([0, nSample], [threshold, threshold], 'k', lw=0.5)
            axarr.set_ylabel('1F amplitude')
            axarr.set_ylim(bottom=0)
            axarr.set_xlabel('Samples')
            plt.tight_layout()
            plt.show()
        elif sequence == 'SEQ':
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



