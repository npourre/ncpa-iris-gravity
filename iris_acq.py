import argparse
from datetime import datetime
import time
import ccs
import vlti

if __name__ == '__main__':
	#Check that the NAOMI loop is closed!
	parser = argparse.ArgumentParser(description="Start with a background and record IRIS data cube")
	parser.add_argument('--duration', '-d', type=float, default=30.0) #second
	args = parser.parse_args()

	tStart = datetime.utcnow().isoformat()[:-7]

	ccs.CcsInit(name='iris_acq.py')
	
	minDit = ccs.DbRead("@waral:Appl_data:ARAL:IRIS:iracq:exposure.MINDIT") 
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
	waral.send("''", "iracqServer", "SETUP", ",,DET.EXP.NAME\ IrisAcq_{0}".format(tStart),verbose=True)

	print("The image integration will last {0} s".format(dit*nDit))
	# Start recording on IRIS
	waral.send("''", "iracqServer", "START", "''",verbose=True)

	time.sleep(args.duration+1)




