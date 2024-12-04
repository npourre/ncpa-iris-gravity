import argparse
from datetime import datetime
import time
import ccs
import vlti

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="prepare iris for NCPA")
    parser.add_argument('tel', type=int, choices=range(5), help="Telescope index. 0 for all telescopes")
    parser.add_argument('--win_size', '-w', type=int, default=10) 
    args = parser.parse_args()
    
    beacon_powers = [20,10,10,15]
    
    if args.tel==0: #all UTs 
       telescopes = [1,2,3,4]
    elif args.tel in [1,2,3,4]: #one UT 
        telescopes = [args.tel]
    else:
        print("WRONG TELESCOPE NUMBER")
        
    # Move the STS offsets from Guide to Align to allow for IRIS guiding
    iss_ssh = vlti.ssh("iss@wvgvlti")
    ccs.CcsInit(name='iris_prepare.py')
    for iTel in telescopes:
        guideU = ccs.DbRead(f"@wvgvlti:Appl_data:VLTI:subSystems:wop{iTel}sts.fsm1GuideU") 
        guideW = ccs.DbRead(f"@wvgvlti:Appl_data:VLTI:subSystems:wop{iTel}sts.fsm1GuideW") 
        # Put in Align offset
        iss_ssh.send(f"wop{iTel}sts", "pscsifControl", "ALIFSTS", f"0,{guideU},0,{guideW}") 
        # Absolute 0 on Guiding offsets
        iss_ssh.send(f"wop{iTel}sts", "pscsifControl", "SETGFSM", f"0,0,0,0") 
        #Start labguiding
    iss_ssh.send("''", 'issifControl', 'STRTLAG', 'AS_SUCH') 
    time.sleep(5)
    

    waral = vlti.ssh("aral@waral")
    waral.send("''", "iracqServer", "FRAME", "-name\ DIT\ -gen\ T\ -store\ T",verbose=True)
    waral.send("''", "iracqServer", "SETUP", ",,DET.WIN.ST\ 1")
    waral.send("''", "iracqServer", "SETUP", f",,DET.WIN.STRX\ {64-args.win_size//2}")
    waral.send("''", "iracqServer", "SETUP", f",,DET.WIN.STRY\ {64-args.win_size//2}")
    waral.send("''", "iracqServer", "SETUP", f",,DET.WIN.NX\ {args.win_size}")
    waral.send("''", "iracqServer", "SETUP", f",,DET.WIN.NY\ {args.win_size}")
    waral.send("''", "iracqServer", "SETUP", ",,DET.DIT\ 0")

    # adjust beacons power
    for iTel in telescopes:
        tcs_ssh = vlti.ssh(f"tcs@wt{iTel}tcs")
        tcs_ssh.send("''", "aubcnServer","SETLLEV",str(beacon_powers[iTel-1]))
        
    # OPTIMIZE GPAO with new power
    # GET GPAO LOOP frequency
    # CLOSE GPAO LOOP