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
# Essentially spectro_ncpa
#
# Launch on ISS
# =============================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process NCPA files")
    parser.add_argument('noll', type=int, help="noll index of the modulation ")
    parser.add_argument('amplitude',type=float,default=0.2, help='Amplitude of the slow modulation ramp [µm]')
    parser.add_argument('repeat', type=int, help="number of repetition for the modulation ")
    parser.add_argument('floop', type=int , help="AO loop frequency")
    parser.add_argument('--timepermode',type=int,default=4, help='time permode (sec)')
    args = parser.parse_args()
    
    out = os.popen('scp 3b_process_probe_grav.py grav@wgv:/vltuser/grav/npourre/')
    print(out)
    wgv = vlti.ssh("grav@wgv")
    wgv._ssh("python /vltuser/grav/npourre/3b_process_probe_grav.py {0} {1} {2} {3} {4}".format(args.noll,args.timepermode,args.amplitude,args.repeat,args.floop))
    time.sleep(1) #sleep more?
    
    out = os.popen('scp grav@wgv:/vltuser/grav/npourre/NCPA_* data/outputs/')
    print(out)
    out = os.popen('scp grav@wgv:/vltuser/grav/npourre/outdat* data/outputs/')
    print(out)
    time.sleep(5)
    
    ncpaname = sorted(glob.glob('data/outputs/NCPA_*'))[-1]
    ncpa = fits.getdata(ncpaname)[0]
    tStart = ncpaname[-24:-5]
    
    
    # ill coded recuperation of the parameters for ploting on iss
    out1 = np.load('data/outputs/outdat1.npy')
    iStartArr,iStopArr, nMeasureArr,nPauseArr = out1[0], out1[1], out1[2], out1[3]
    out2 = np.load('data/outputs/outdat2.npy')
    threshold,nSample = out2[0], out2[1], 
    mix_f = np.load('data/outputs/outdat3.npy')
    out4 = np.load('data/outputs/outdat4.npy')
    t,flux = out4[0], out4[1]
    out5 = np.load('data/outputs/outdat5.npy')
    freq,psd = out5[0],out5[1]
    mix_2f = np.load('data/outputs/outdat6.npy')
    ncparray = np.load('data/outputs/outdat7.npy')
    ncpa = ncpa[2:14]
    filename = np.load('data/outputs/outdat8.npy')

    iStartArr,iStopArr = iStartArr.astype(int),iStopArr.astype(int)

    # Plot NCPA
    fig, axarr = plt.subplots(1, 1)
    ncpa_rms = np.sqrt(np.mean(ncpa**2))
    axarr.plot(ncparray*1e3, '.-', label='({0:.0f} nmRMS)'.format(np.mean(ncparray)*1e3))
    axarr.set_xlabel('Repetition of Noll {0}'.format(args.noll))
    axarr.set_ylabel('NCPA [nmRMS]')
    axarr.set_title(filename)
    axarr.set_xlim(0, len(ncparray))
    axarr.set_ylim(-np.abs(np.min(ncparray*1e3))*1.1,np.abs(np.max(ncparray*1e3))*1.1)
    axarr.grid()
    axarr.legend()
    #fig.savefig('data/outputs/Fig-NcpaResults_{0}.pdf'.format(tStart))
    plt.show()
    print("Average NCPA noll {0} amplitude ({1:.0f} nmRMS)".format(args.noll,np.mean(ncparray)*1e3))
    #Plot amplitude of 1.f modulation
    fig, axarr = plt.subplots(1, 1, sharex=True, sharey=True, figsize=(12, 4))
    iTel = 0
    for iZ in range(args.repeat):
        xStart = iStartArr[iTel]+iZ*(nMeasureArr[iTel]+nPauseArr[iTel])
        xStop = iStartArr[iTel]+iZ*(nMeasureArr[iTel]+nPauseArr[iTel]) + nMeasureArr[iTel]
        axarr.add_patch(patches.Rectangle((xStart,0), xStop-xStart, 420, alpha=0.2, color='grey'))
        axarr.text((xStart+xStop)/2.0, 400, 'Z{0}'.format(args.noll), va='top', ha='center')
    axarr.plot(mix_f)
    axarr.plot([0, nSample], [threshold, threshold], 'k', lw=0.5)
    axarr.set_ylabel('1F amplitude')
    axarr.legend()
    axarr.set_xlim(0, np.max(iStartArr[iTel])+nMeasureArr[-1]*14+nPauseArr[-1]*11)
    axarr.set_ylim(bottom=0)
    axarr.set_xlabel('Samples')
    #fig.savefig('data/outputs/Fig-NcpaDemodulation_{0}.pdf'.format(tStart))
    plt.show()
    
    iStart = int(iStartArr[iTel])
    iStop = int(iStopArr[iTel])
    # Multiplot diagnostic
    plt.figure(figsize=(8,6))
    plt.subplot(2,2,1)
    plt.title('Flux')
    plt.xlabel('Image number')
    plt.plot(flux)
    plt.grid(True)
    plt.subplot(2,2,2)
    plt.title('PSD')
    plt.xlabel('Freq')
    plt.plot(freq,psd)
    plt.grid(True)
    plt.subplot(2,2,3)
    plt.plot(t[iStart:iStop],mix_f[iStart:iStop])
    plt.title('mix_f')
    plt.grid(True)
    plt.subplot(2,2,4)
    plt.title('mix_2f')
    plt.plot(t[iStart:iStop],mix_2f[iStart:iStop])
    plt.grid(True)
    
    plt.tight_layout()
    #plt.savefig('data/outputs/Fig-plots_{0}.pdf'.format(tStart))
    plt.show()
    os.system('rm data/outputs/outdat*')
