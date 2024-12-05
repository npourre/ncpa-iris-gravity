
from datetime import datetime
import time
import ccs
import vlti



def iris_acquisition(duration,name):
    tStart = datetime.utcnow().isoformat()[:-7]
    ccs.CcsInit(name='iris_acq.py')
    
    dit = ccs.DbRead("@waral:Appl_data:ARAL:IRIS:iracq:exposure.DIT") 
    #RECORD IMAGE
    nDit = args.duration/(dit)
    # Prepare IRIS
    waral = vlti.ssh("aral@waral")
    waral.send("''", "iracqServer", "FRAME", "-name\ DIT\ -gen\ T\ -store\ T",verbose=True)
    waral.send("''", "iracqServer", "FRAME", "-name\ INT\ -gen\ T\ -store\ T")
    waral.send("''", "iracqServer", "SETUP", ",,DET.NDIT\ {0}".format(nDit))
    waral.send("''", "iracqServer", "SETUP", ",,DET.DIT\ {0}".format(dit)) 
    waral.send("''", "iracqServer", "SETUP", ",,DET.DITDELAY\ 0")
    waral.send("''", "iracqServer", "SETUP", ",,DET.FILE.CUBE.ST\ T")
    waral.send("''", "iracqServer", "SETUP", ",,DET.EXP.NAMING.TYPE\ Request-Naming")
    if not args.name=="":
        waral.send("''", "iracqServer", "SETUP", ",,DET.EXP.NAME\ {0}".format(args.name),verbose=True)
    else:
        waral.send("''", "iracqServer", "SETUP", ",,DET.EXP.NAME\ IrisAcq_{0}".format(tStart),verbose=True)

    print("The image integration will last {0} s".format(dit*nDit))
    # Start recording on IRIS
    waral.send("''", "iracqServer", "START", "''",verbose=True)

    time.sleep(args.duration+1)




