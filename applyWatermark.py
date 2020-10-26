import os
import re
import cards
import argparse
import json
import shutil

# pip install pillow
from PIL import Image

# add arg parsing to pass in a single decklist/folder of decklists
DECKLIST_SUFFIX = ".txt"

DEFAULT_DECKLIST_DIRECTORY_ROOT = ".%sdecklists" % os.path.sep
DEFAULT_JSON_DIRECTORY_ROOT  = ".%s" % os.path.sep
DEFAULT_WATERMARK_MAPPING_DIRECTORY_ROOT  = ".%swatermarkMapping" % os.path.sep

DEFAULT_WATERMARK_MAPPING_FILENAME = "mapping.json"

IMAGE_SUFFIX = ".jpg"
IMAGE_DIRECTORY_ROOT = "./magic_images"

MAINDECK_REGEX = "\s*[mM]ain\s*[dD]eck:?\s*"
SIDEBOARD_REGEX = "\s*[sS]ide\s*[bB]oard:?\s*"

BASIC_LAND_NAMES = ["Forest", "Island", "Mountain", "Plains", "Swamp"]

allCards = None

def getDecklistDirectory(args):
	if args and args.decklistDirectory:
		return args.decklistDirectory
	else:
		return DEFAULT_DECKLIST_DIRECTORY_ROOT

def getCardJsonDirectory(args):
	if args and args.jsonDirectory:
		return args.jsonDirectory
	else:
		return DEFAULT_JSON_DIRECTORY_ROOT

def getWatermarkMappingDirectory(args):
	if args and args.watermarkMapping:
		return args.watermarkMapping
	else:
		return DEFAULT_WATERMARK_MAPPING_DIRECTORY_ROOT

def getSetToWatermarkMapping(args):
	mappingDirectory = getWatermarkMappingDirectory(args)
	mappingFilepath = os.path.join(mappingDirectory, DEFAULT_WATERMARK_MAPPING_FILENAME)

	with open(mappingFilepath, 'r', encoding="utf-8") as custom_cards_file:
		mapping_contents = json.load(custom_cards_file)
		return mapping_contents
	
	return {}

# copied from magic art downloader, need to combine at some point
def populateInitialDecklistDict(subDir, fileName):
	# load it and cram into dictionary
	decklistDict = {}
	fileContents = open(os.path.join(subDir, fileName), 'r').read()
	for line in fileContents.split("\n"):
		maindeck_line = re.search(MAINDECK_REGEX, line)
		if maindeck_line:
			continue

		sideboard_line = re.search(SIDEBOARD_REGEX, line)
		if sideboard_line:
			continue

		matches = re.search("(\d*)x?(\s*)(.*)", line)
		cardCount = 1 if matches.group(1) == '' else int(matches.group(1))
		cardName = matches.group(3)

		if cardName:
			decklistDict[cardName] = decklistDict.get(cardName, 0) + cardCount

	#addDoubleFacedCardsToDict(decklistDict)
	return decklistDict

def fixCardName(cardName):
	# Convert Fire / Ice, Fire//Ice into Fire_Ice
	splitCardName = re.search("^(\S*?)\s*\/\/?\s*(\S*)", cardName)
	if splitCardName:
		newCardName = splitCardName.group(1).capitalize() + "_" + splitCardName.group(2).capitalize()
		return newCardName

	return cardName

def deleteExistingDecklistImages(subDir, files):
	for fileName in files:
		if fileName.endswith(IMAGE_SUFFIX):
			os.remove(os.path.join(subDir, fileName))

def copyAndApplyWatermarkToCardImages(mappingDict, decklistDict, subDir):
	playerName = re.search("(\w+)$", subDir).group(0)
	setsDict = mappingDict[playerName]

	for initialCardName, cardCount in decklistDict.items():
		cardName = fixCardName(initialCardName)

		if not initialCardName in allCards.getAllCardnames():
			print("Couldn't find card name %s!!!" % cardName)

		if initialCardName == "Armed // Dangerous":
			continue

		playerToWatermark = None
		for cardSet in setsDict.keys():
			if cardSet in allCards.getAllCards()[initialCardName]['printings']:
				playerToWatermark = setsDict[cardSet]
				break

		if not playerToWatermark:
			raise Exception("Couldn't find printing for card %s for player %s.  Printings: %s" % (cardName, playerName, allCards.getAllCards()[initialCardName]['printings']))

		suffixNum = 1
		while suffixNum <= cardCount:
			inputFilepath = os.path.join(IMAGE_DIRECTORY_ROOT, cardName + IMAGE_SUFFIX)
			tempOutputFilepath = os.path.join(subDir, cardName + "_" + str(suffixNum) + "_TEMP" + IMAGE_SUFFIX)
			outputFilepath = os.path.join(subDir, cardName + "_" + str(suffixNum) + IMAGE_SUFFIX)

			if cardName in BASIC_LAND_NAMES:
				shutil.copy(inputFilepath, outputFilepath)
				suffixNum += 1
				continue

			shutil.copy(inputFilepath, tempOutputFilepath)

			

			base_image = Image.open(tempOutputFilepath)
			base_image_width, base_image_height = base_image.size

			watermarkPosX = int(base_image_width * 0.825)
			watermarkPosY = int(base_image_height * 0.555)

			watermarkSize = int(base_image_width * 0.10), int(base_image_height * 0.10)

			watermark_full = Image.open('./watermarkMapping/%s.png' % playerToWatermark)
			watermark_full.thumbnail(watermarkSize, Image.ANTIALIAS)

			# add watermark to your image
			base_image.paste(watermark_full, (watermarkPosX,watermarkPosY), mask=watermark_full)
			base_image.save(outputFilepath)

			os.remove(tempOutputFilepath)

			suffixNum += 1

def applyWatermarksToCards(args):
	watermarkMapping = getSetToWatermarkMapping(args)
	print(watermarkMapping)

	for subDir, dirs, files in os.walk(getDecklistDirectory(args)):
		for fileName in files:
			if fileName == "TestCards.txt":
				continue
			if fileName.endswith(DECKLIST_SUFFIX):
				filePath = os.path.join(subDir, fileName)
				decklistDict = populateInitialDecklistDict(subDir, fileName)
				deleteExistingDecklistImages(subDir, files)
				copyAndApplyWatermarkToCardImages(watermarkMapping, decklistDict, subDir)


parser = argparse.ArgumentParser()
parser.add_argument('-d', '--decklistDirectory', help="Directory of the source decklists to check")
parser.add_argument('-j', '--jsonDirectory', help="Directory of the source json to check")
parser.add_argument('-m', '--watermarkMapping', help="Filepath of the set -> image to replace with directory.  Directory will contain mapping.txt and images in same folder.")
args = parser.parse_args()
print(args)


allCards = cards.Cards(getCardJsonDirectory(args))

applyWatermarksToCards(args)


print("ROFLMAO")