import os
import re
import argparse
import json
import shutil
import sys
sys.path.append('../')
import cards

# add arg parsing to pass in a single decklist/folder of decklists
DECKLIST_SUFFIX = ".txt"

DEFAULT_DECKLIST_DIRECTORY_ROOT = ".%sdecklists" % os.path.sep
DEFAULT_JSON_DIRECTORY_ROOT  = "../.%s" % os.path.sep
DEFAULT_WATERMARK_MAPPING_DIRECTORY_ROOT  = ".%swatermarkMapping" % os.path.sep

DEFAULT_WATERMARK_MAPPING_FILENAME = "mapping.json"

IMAGE_SUFFIX = ".jpg"
IMAGE_DIRECTORY_ROOT = "./magic_images"

MAINDECK_REGEX = "\s*[mM]ain\s*[dD]eck:?\s*"
SIDEBOARD_REGEX = "\s*[sS]ide\s*[bB]oard:?\s*"

BASIC_LAND_NAMES = ["Forest", "Island", "Mountain", "Plains", "Swamp"]

LEGAL_SETS = ["LEA","LEB","2ED","3ED","4ED","5ED","6ED","7ED","8ED","9ED","10E","M10","M11","M12","M13","M14","M15","ORI","M19","M20","M21","ARN","ATQ","LEG","DRK","FEM","ICE","HML","ALL","MIR","VIS","WTH","TMP","STH","EXO","USG","ULG","UDS","MMQ","NEM","PCY","INV","PLS","APC","ODY","TOR","JUD","ONS","LGN","SCG","MRD","DST","5DN","CHK","BOK","SOK","RAV","GPT","DIS","CSP","TSP","PLC","FUT","LRW","MOR","SHM","EVE","ALA","CON","ARB","ZEN","WWK","ROE","SOM","MBS","NPH","ISD","DKA","AVR","RTR","GTC","DGM","THS","BNG","JOU","KTK","FRF","DTK","BFZ","OGW","SOI","EMN","KLD","AER","AKH","HOU","XLN","RIX","DOM","GRN","RNA","WAR","ELD","THB","IKO","ZNR","KHM"]

allCards = None

def getCardJsonDirectory(args):
	if args and args.jsonDirectory:
		return args.jsonDirectory
	else:
		return DEFAULT_JSON_DIRECTORY_ROOT


parser = argparse.ArgumentParser()
parser.add_argument('-j', '--jsonDirectory', help="Directory of the source json to check")
args = parser.parse_args()
print(args)


allCards = cards.Cards(getCardJsonDirectory(args))
allSets = {}

for cardname, card in allCards.getAllCards().items():
	if(card and card['convertedManaCost'] >= 7):
		for printing in card['printings']:
			if printing not in LEGAL_SETS:
				continue
			if not printing in allSets:
				allSets[printing] = []
			allSets[printing].append(card)
#print(allCards)

print(allSets.keys())

for cardSetName, cardSet in allSets.items():
	print(str(cardSetName) + " " + str(len(cardSet)))
	#print(cardSet)