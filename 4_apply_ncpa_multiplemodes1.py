#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 30 16:17:34 2023

@author: pourren
"""
# =============================================================================
# Copy that apply NCPA
# =============================================================================

import argparse
from datetime import datetime
import time
import os
import ccs
import vlti
from PySide2 import QtWidgets
import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
import glob

# =============================================================================
# LAUNCH ON ISS
# =============================================================================
def apply_offset(ncpa_offset, indTel, noll_start, noll_end, user):
    modal_offsets = np.zeros(30, dtype=np.float32)
    if ncpa_offset.shape[0]==1:
        modal_offsets[noll_start-2:noll_end-1] = -ncpa_offset[0]
    else:
        modal_offsets[noll_start-2:noll_end-1] = -ncpa_offset[indTel]
    modes_str = ' '.join(map(str, modal_offsets))
    print("NCPA to apply (tip, tilt, defocus, ...) on UT{0} : \n ".format(indTel+1)+modes_str)
    if user==1:
        appl = input('Apply these NCPA on UT{0} ? (y/n)'.format(indTel+1))
    else:
        appl = 'y'
    if appl=='y' or appl=='Y' or appl=='yes' or appl=='Yes' or appl=='YES':
        # SEND THE NEW ONE to sgw
        wgpNao = vlti.ssh("gpao{0}@wgp{0}ao".format(indTel+1))
        # SEND THE NEW ONE TO CDMS
        wgpNao.send("wgp{0}ao".format(indTel+1), "gpoControl", "SETWF", "\"-type REL -modes {0}  \"".format(modes_str),verbose=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Apply NCPA")
    parser.add_argument('tel', type=int, choices=range(5), help="Telescope index; use 0 for all four at once.")
    parser.add_argument('mode_start', type=int , help="start mode Noll index")
    parser.add_argument('mode_end', type=int , help="end mode Noll index")
    parser.add_argument('name_acquisition', type=str, help="name of the IRIS acquisition")
    parser.add_argument('--user_input','-u', type=int,default=1 , help="Ask for user validation to apply ncpa. 0/1")
    args = parser.parse_args()
    
    tStart = args.name_acquisition.split('_')[1]
    #get the last NCPA file
    ncpa_file = sorted(glob.glob('/vltuser/iss/temp_ncpa/NCPA_*{0}*.npy'.format(tStart)))[-1]
    print('Applying {0} '.format(ncpa_file))
    ncpas = -np.load(ncpa_file)


    ncpas = np.array(ncpas).mean(1) #average on the different repetitions


    # Prepare GPAO(s)
    if args.tel==0: #all UTs measurements
        for indTel in range(4):
            apply_offset(ncpas,indTel,args.mode_start,args.mode_end, args.user_input)
    elif args.tel in [1,2,3,4]: #one UT measurement
        apply_offset(ncpas,args.tel-1,args.mode_start,args.mode_end, args.user_input)
    else:
        print("WRONG TELESCOPE NUMBER")


