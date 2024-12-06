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
import numpy as np
from astropy.io import fits
import glob

# =============================================================================
# LAUNCH ON ISS
# =============================================================================
def apply_offset_PAR(ncpa_offset, indTel, noll_start, noll_end, user):
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

def apply_offset_SEQ(ncpa_offset, indTel, noll, user):
    modal_offsets = np.zeros(30, dtype=np.float32)
    if ncpa_offset.shape[0]==1:
        modal_offsets[noll-2] = -np.mean(ncpa_offset[0])
    else:
        modal_offsets[noll-2] = -np.mean(ncpa_offset[indTel])
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


def E_apply_ncpa(tel, mode_start, mode_end, name_acquisition, sequence, user_input, temp_folder, gain):
    tStart = name_acquisition.split('_')[1]
    #get the last NCPA file
    ncpa_file = sorted(glob.glob(os.path.join(temp_folder,'NCPA_*{0}*.npy'.format(tStart))))[-1]
    print('Applying {0} '.format(ncpa_file))
    ncpas = -np.load(ncpa_file)

    ncpas = np.array(ncpas).mean(1) * gain #average on the different repetitions

    # Prepare GPAO(s)
    if sequence == 'PAR':
        if tel==0: #all UTs measurements
            for indTel in range(4):
                apply_offset_PAR(ncpas,indTel,mode_start,mode_end, user_input)
        elif tel in [1,2,3,4]: #one UT measurement
            apply_offset_PAR(ncpas,tel-1, mode_start, mode_end, user_input)
        else:
            print("WRONG TELESCOPE NUMBER")
    elif sequence == 'SEQ':
        if tel==0: #all UTs measurements
            for indTel in range(4):
                apply_offset_SEQ(ncpas,indTel,mode_start, user_input)
        elif tel in [1,2,3,4]: #one UT measurement
            apply_offset_SEQ(ncpas,tel-1, mode_start, user_input)
        else:
            print("WRONG TELESCOPE NUMBER")
    else:
        raise ValueError('Sequence argument is not SEQ and not PAR.')
