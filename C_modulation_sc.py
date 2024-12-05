#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May 30 16:16:17 2023

@author: pourren
"""
# =============================================================================
# Essentially spectro_ncpa
#
# Launch on ISS
# =============================================================================

import argparse
from datetime import datetime
import time
import ccs
import vlti


def C_modulation_sc(tel, mode_start, mode_end, repeat, sequence, floop, name_acquisition, duration, dit, bck):
    ips = [4,3,2,1]
    ip_num = ips[tel-1]
    wgv = vlti.ssh("grav@wgv")

    # Prepare SPECTRO
    #wgv.send("''", "ngcircon_NGCIR2", "FRAME", "-function DET.ACQ1.EXTNAME IMAGING_DATA_SC")
    wgv.send("''", "ngcircon_NGCIR2", "SETUP","\",,DET.READ.CURNAME Uncorr_6slices_10MHz\"",verbose=True) 
    wgv.send("''", "ngcircon_NGCIR2", "SETUP", "\",,DET.SEQ.DIT {0}\"".format(dit),verbose=True)
    nDit = int(duration/(dit*1))
    wgv.send("''", "ngcircon_NGCIR2", "SETUP","\",,DET2.FRAM.FORMAT cube-ext\"",verbose=True)
    wgv.send("''", "ngcircon_NGCIR2", "SETUP","\",,DET.FRAM.NAMING Request\"",verbose=True)
    
    # Prepare GPAO(s)
    if sequence == 'PAR':
        wgpNao = vlti.ssh("gpao{0}@wgp{0}ao".format(tel))
        wgpNao.send("wgp{0}sgw".format(tel), "spaccsServer", "SETUP", "\"HOAcqDisturb.FILENAME $INS_ROOT/SYSTEM/SPARTA/RTCDATA/NcpaModulation_noll{0}to{1}_tel{2}_f{3}.fits\"".format(mode_start, mode_end, tel, floop))
        wgpNao.send("wgp{0}sgw".format(tel), "spaccsServer", "SETUP", f"HOAcqDisturb.CYCLES\ {repeat}")
        wgpNao.send("wgp{0}sgw".format(tel), "spaccsServer", "SETUP", "HOAcqDisturb.START_AT_FC\ 0")
    elif sequence == 'SEQ':
        wgpNao = vlti.ssh("gpao{0}@wgp{0}ao".format(tel))
        wgpNao.send("wgp{0}sgw".format(tel), "spaccsServer", "SETUP", "\"HOAcqDisturb.FILENAME $INS_ROOT/SYSTEM/SPARTA/RTCDATA/NcpaModulation_noll{0}_tel{1}_f{2}.fits\"".format(mode_start, tel, floop))
        wgpNao.send("wgp{0}sgw".format(tel), "spaccsServer", "SETUP", "HOAcqDisturb.CYCLES\ 1")
        wgpNao.send("wgp{0}sgw".format(tel), "spaccsServer", "SETUP", "HOAcqDisturb.START_AT_FC\ 0")


    if bck:
        # Take background 
        tStart = name_acquisition.split('_')[1]
        wgv.send("''", "gviControl", "SETUP", "\",,INS.SHUT11.ST F INS.SHUT12.ST F INS.SHUT13.ST F INS.SHUT14.ST F \"",verbose=True) # Close shutters
        #time.sleep(10)
        wgv.send("''", "ngcircon_NGCIR2", "SETUP", "\",,DET.NDIT {0}\"".format(100))
        wgv.send("''", "ngcircon_NGCIR2", "SETUP", "\",,DET.FRAM.FILENAME GravNcpa_{0}_bckg\"".format(tStart),verbose=True)
        wgv.send("''", "ngcircon_NGCIR2", "START", "\"\"")
        time.sleep(100*dit+1)
        #wgv.send("''", "gviControl", "SETUP", "\",,INS.SHUT1.ST T INS.SHUT2.ST T INS.SHUT13.ST T INS.SHUT14.ST T \"") # Open shutters

    wgv.send("''", "gviControl", "SETUP", "\",,INS.SHUT11.ST F INS.SHUT12.ST F INS.SHUT13.ST F INS.SHUT14.ST F \"",verbose=True) # Close shutters
    wgv.send("''", "gviControl", "SETUP", "\",,INS.SHUT1{0}.ST T \"".format(ip_num),verbose=True)
    # Start Field Guiding 
    time.sleep(2)
    wgv.send("''", "gvttpControl", "STRTLP", "FIELD_IMAGER",verbose=True)
    time.sleep(5)
    # Start recording on SC
    wgv.send("''", "ngcircon_NGCIR2", "SETUP", "\",,DET.NDIT {0}\"".format(nDit),verbose=True)
    wgv.send("''", "ngcircon_NGCIR2", "SETUP", "\",,DET.ACQ1.QUEUE {0}\"".format(nDit),verbose=True)
    wgv.send("''", "ngcircon_NGCIR2", "SETUP", "\",,DET.FRAM.FILENAME {0}\"".format(name_acquisition),verbose=True)
    wgv.send("''", "ngcircon_NGCIR2", "START", "\"\"",verbose=True)
    time.sleep(1)

    # Start modulation on GPAO
    if (tel>=1) and (tel<=4):
        wgpNao.send("wgp{0}sgw".format(tel), "spaccsServer", "EXEC", "HOAcqDisturb.run",verbose=True)
    else:
        print('Wrong telescope number')


