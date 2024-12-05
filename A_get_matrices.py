#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 30 16:15:28 2023

@author: pourren
"""
# =============================================================================
# Launch on ISS
# Create folders and get matrices from sparta
# =============================================================================

import os
import vlti

def get_matrices_data(iTel):
    wgpNsgw = vlti.ssh("gpao{0}@wgp{0}sgw".format(iTel))
    # save MODE2SLOPES from sparta
    wgpNsgw.send("wgp{0}sgw".format(iTel), "spaccsServer", "SAVE", "\"-object HOAcq.DET1.MODETOSLOPE  -filename MODE2SLOPE{0}.fits \"".format(iTel),verbose=True)
    # send to ISS directory
    os.system('scp gpao{0}@wgp{0}sgw:/data/GPAO{0}/INS_ROOT/SYSTEM/SPARTA/RTCDATA/MODE2SLOPE{0}.fits data '.format(iTel))

    # save rotmap from sparta
    wgpNsgw.send("wgp{0}sgw".format(iTel), "spaccsServer", "SAVE", "\"-object HOAcq.DET1.ROTATION_MATRIX  -filename ROTATION_MATRIX{0}.fits \"".format(iTel),verbose=True)
    # send to ISS directory
    os.system('scp gpao{0}@wgp{0}sgw:/data/GPAO{0}/INS_ROOT/SYSTEM/SPARTA/RTCDATA/ROTATION_MATRIX{0}.fits data '.format(iTel))

    # save scramble matrix from sparta
    wgpNsgw.send("wgp{0}sgw".format(iTel), "spaccsServer", "SAVE", "\"-object HORecn.WFS_SLP_UNSCR_MAP  -filename WFS_SLP_UNSCR_MAP{0}.fits \"".format(iTel),verbose=True)
    # send to ISS directory
    os.system('scp gpao{0}@wgp{0}sgw:/data/GPAO{0}/INS_ROOT/SYSTEM/SPARTA/RTCDATA/WFS_SLP_UNSCR_MAP{0}.fits data '.format(iTel))

def A_get_matrices(tel):
    if not os.path.isdir('data'):
        os.system('mkdir data')
    if not os.path.isdir('data/default_refslopes'):
        os.system('mkdir data/default_refslopes')
    if not os.path.isdir('data/modified_refslopes'):
        os.system('mkdir data/modified_refslopes')
    if not os.path.isdir('data/modulations'):
        os.system('mkdir data/modulations')
    if not os.path.isdir('data/outputs'):
        os.system('mkdir data/outputs')

    if tel==0: #all UTs measurements
        for iTel in range(1,5):
            get_matrices_data(iTel)
    elif tel in [1,2,3,4]: #one UT measurement
        get_matrices_data(tel)
    else:
        print("WRONG TELESCOPE NUMBER")


