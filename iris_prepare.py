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
        





