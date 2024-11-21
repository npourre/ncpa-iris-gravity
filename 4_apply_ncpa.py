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
def apply_offset(ncpa_offset, indTel, noll):
    modal_offsets = np.zeros(30, dtype=np.float32)
    if ncpa_offset.shape[0]==1:
        modal_offsets[noll-2] = -np.mean(ncpa_offset[0])
    else:
        modal_offsets[noll-2] = -np.mean(ncpa_offset[indTel])
    modes_str = ' '.join(map(str, modal_offsets))
    print("NCPA to apply (tip, tilt, defocus, ...) on UT{0} : \n ".format(indTel+1)+modes_str)
    appl = input('Apply these NCPA on UT{0} ? (y/n)'.format(indTel+1))
    if appl=='y':
        # SEND THE NEW ONE to sgw
        wgpNao = vlti.ssh("gpao{0}@wgp{0}ao".format(indTel+1))
        # SEND THE NEW ONE TO CDMS
        wgpNao.send("wgp{0}ao".format(indTel+1), "gpoControl", "SETWF", "\"-type REL -modes {0}  \"".format(modes_str),verbose=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Apply NCPA")
    parser.add_argument('tel', type=int, choices=range(5), help="Telescope index; use 0 for all four at once.")
    parser.add_argument('noll', type=int, help="noll index of the modulation ")
    args = parser.parse_args()
    
    #get the last NCPA file
    ncpa_file = sorted(glob.glob('data/outputs/NCPA_*.npy'))[-1]
    print('Applying {0} '.format(ncpa_file))
    ncpa_offset = -np.load(ncpa_file)

    # Prepare GPAO(s)
    if args.tel==0: #all UTs measurements
        for indTel in range(4):
            apply_offset(ncpa_offset,indTel,args.noll)
    elif args.tel in [1,2,3,4]: #one UT measurement
        apply_offset(ncpa_offset,args.tel-1,args.noll)
    else:
        print("WRONG TELESCOPE NUMBER")


