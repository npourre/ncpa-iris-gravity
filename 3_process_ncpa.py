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
    parser.add_argument('tel', type=int, choices=range(5), help="Telescope index; use 0 for all four at once.")
    parser.add_argument('noll', type=int, help="noll index of the modulation ")
    parser.add_argument('repeat', type=int, help="number of repetition for the modulation ")
    parser.add_argument('floop', type=int , help="AO loop frequency")
    parser.add_argument('--timepermode','-t',type=int,default=4, help='time permode (sec)')
    args = parser.parse_args()
    
    amplitude_slow = 0.2 #µm rms
    out = os.popen('scp 3b_process_probe.py aral@waral:/vltuser/aral/npourre/')
    print(out)
    wgv = vlti.ssh("aral@waral")
    wgv._ssh("python /vltuser/aral/npourre/3b_process_probe.py {0} {1} {2} {3} {4} {5}".format(args.tel, args.noll, args.timepermode, amplitude_slow, args.repeat, args.floop))
    time.sleep(1) #sleep more?
    
    out = os.popen('scp aral@waral:/vltuser/aral/npourre/NCPA_* data/outputs/')
    print(out)
    out = os.popen('scp aral@waral:/vltuser/aral/npourre/outdat* data/outputs/')
    print(out)
    time.sleep(5)
    
    ncpaname = sorted(glob.glob('data/outputs/NCPA_*'))[-1]
    ncpaArr = np.load(ncpaname)
    tStart = ncpaname.split('_')[1].split('.')[0]
    
    # ill coded recuperation of the parameters for ploting on iss
    out1 = np.load('data/outputs/outdat1.npy')
    iStartArr,iStopArr, nMeasureArr,nPauseArr = out1[0], out1[1], out1[2], out1[3]
    out2 = np.load('data/outputs/outdat2.npy')
    threshold,nSample = out2[0], out2[1], 
    mix_f_Arr = np.load('data/outputs/outdat3.npy')
    filename = np.load('data/outputs/outdat4.npy')

    iStartArr,iStopArr = iStartArr.astype(int),iStopArr.astype(int)

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
    if args.tel==0 and ncpaArr.shape[0]==4: #4 UTs at once
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
    elif (args.tel in [1,2,3,4]) and ncpaArr.shape[0]==1: #one UT measurement
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
    
    os.system('rm data/outputs/outdat*')

