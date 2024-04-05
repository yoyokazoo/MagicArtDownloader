import os
import re
import shutil

import urllib.request
import string

# pip install pillow
from PIL import Image

# todo: Move all the scryfall-specific stuff to its own file to allow for scraping from other sites, keep this code relatively clean, etc.
URL_PREFIX = "https://scryfall.com/search?as=grid&dir=asc&order=released&q=%21%22";
URL_SUFFIX = "%22&unique=prints";

IMAGE_IN_SOURCE_REGEX = "\s*<img class=\"card (.*?) border.*title=\"(.*?)\((.*?)\)\".*?(data-rotate=\"(.*?)\" )?src=\"(.*\.jpg).*"

CARD_SETS_TO_IGNORE = [
	"PW12", "P09",
	"PWP09", "PWP10", "PWP11", "PWP12", # planeswalker packs
	"F10", "F11", "F12", "F13", "F14", "F15", "F16", "F17", "F18", # friday night magic
	"V17", # from the vault
	"EXP", "MPS", "MP2", # expeditions/masterpieces/invocations
	"PAL99", "PAL00", "PAL01", "PAL02", "PAL03", "PAL04", "PAL05", "PAL06", # arena league
	"PM15", "PG08", "PPRE", "PM11", "POGW", "PJOU", "PDKA", "PISD", "PPLS", "PAVR", # should just disallow 4 digit set codes that start with P
	"PNPH", "PMBS", "PRTR", "PSOM", "PSAL", "PS15", "JGP" # other
]

IMAGE_SUFFIX = ".png"
DECKLIST_SUFFIX = ".txt"

DOUBLE_FACED_CARD_DICTIONARY_PATH =  "./doubleFacedCardDict.txt"
IMAGE_DIRECTORY_ROOT = "./magic_images"
DECKLIST_DIRECTORY_ROOT = "./decklists"

MAINDECK_REGEX = "\s*[mM]ain\s*[dD]eck:?\s*"
SIDEBOARD_REGEX = "\s*[sS]ide\s*[bB]oard:?\s*"

SET_CODE_REGEX = "(\s*\((\w\w\w)\))$"


RECOPY_IMAGES = True
# todo: if format-specific land doesn't exist, just download the base version and make a copy with the format-specific version
USE_FORMAT_SPECIFIC_LANDS = True
DO_MPCFILL_POSTPROCESSING = True

# urllib2 junk
user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
headers = { 'User-Agent' : user_agent }



BASIC_LAND_NAMES = ["Forest", "Island", "Mountain", "Plains", "Swamp"]

def reprocessImageForMPCFill(oldImagePath, newImagePath):
	# Thanks ChatGPT, I'm lazy!
	# Open the original image
	original_image = Image.open(oldImagePath)

	# Calculate the coordinates for cropping
	left = (original_image.width - 686) // 2
	top = (original_image.height - 976) // 2
	right = left + 686
	bottom = top + 976

	# Crop the image
	cropped_image = original_image.crop((left, top, right, bottom))

	# Create a new black image
	new_image = Image.new('RGB', (816, 1110), (0, 0, 0))

	# Calculate the coordinates for pasting
	paste_left = (new_image.width - cropped_image.width) // 2
	paste_top = (new_image.height - cropped_image.height) // 2
	paste_right = paste_left + cropped_image.width
	paste_bottom = paste_top + cropped_image.height

	# Paste the cropped image onto the black image
	new_image.paste(cropped_image, (paste_left, paste_top))

	# Save the new image
	new_image.save(newImagePath)

def isPartOfDoubleFacedCardDict(doubleFacedCardDict, cardName):
	for frontName, backName in doubleFacedCardDict.items():
		if frontName == cardName or backName == cardName:
			return True

	return False

def isDoubleFacedFrontFace(doubleFacedCardDict, cardName):
	for frontName, backName in doubleFacedCardDict.items():
		if frontName == cardName:
			return True

	return False

def isDoubleFacedBackFace(doubleFacedCardDict, cardName):
	for frontName, backName in doubleFacedCardDict.items():
		if backName == cardName:
			return True

	return False

def fixCardName(cardName, formatName):
	# Convert Fire / Ice, Fire//Ice into Fire_Ice
	splitCardName = re.search("^(\S*?)\s*\/\/?\s*(\S*)", cardName)
	if splitCardName:
		newCardName = splitCardName.group(1).capitalize() + "_" + splitCardName.group(2).capitalize()
		cardName = newCardName # should be cardName = newCardName so we can fix all screwups?

	# Circle of Protection: Blue into Circle of Protection Blue
	colonCardName = re.search("([^:]*):\s*([^:]*)", cardName)
	if colonCardName:
		newCardName = colonCardName.group(1).capitalize() + "_" + colonCardName.group(2).capitalize()
		cardName = newCardName # should be cardName = newCardName so we can fix all screwups?

	# Convert Plains into PlainsModern, PlainsStandard, PlainsTestCard etc.
	# so you can associate different basic land arts with different decklists
	#print("Card name: %s Format name: %s" % (cardName, formatName))
	if USE_FORMAT_SPECIFIC_LANDS and cardName in BASIC_LAND_NAMES:
		cardName = cardName + formatName

	cardName = cardName.replace("â€™", "")
	cardName = cardName.replace("\t", " ")

	return cardName

def getUrlSanitizedCardnameAndSet(cardName):
	set_code = None
	set_code_match = re.search(SET_CODE_REGEX, cardName)
	if set_code_match:
		set_code_text = set_code_match.group(1)
		set_code = set_code_match.group(2)
		cardName = cardName[:-len(set_code_text)]

	# https://www.degraeve.com/reference/specialcharacters.php
	cardName = cardName.replace("'", "")
	cardName = cardName.replace("(", "%28")
	cardName = cardName.replace(")", "%29")
	cardName = cardName.replace("!", "%33")
	cardName = cardName.replace("\"", "%34")
	cardName = cardName.replace(":", "%3A")
	cardName = cardName.replace(" ", "+")
	cardName = cardName.replace("_", "//") # change Fire_Ice to Fire//Ice
	return cardName, set_code

def addDoubleFacedCardsToDict(decklistDict):
	cardsToAdd = {}
	for cardName, cardCount in decklistDict.items():
		otherFaceCardName = doubleFacedCardDict.get(cardName, None)
		if otherFaceCardName != None:
			cardsToAdd[otherFaceCardName] = cardCount

	for cardName, cardCount in cardsToAdd.items():
		decklistDict[cardName] = cardCount

def prepareMagicImagesDirectory():
	# create magic images directory, if necessary
	if not os.path.isdir(IMAGE_DIRECTORY_ROOT):
		os.mkdir(IMAGE_DIRECTORY_ROOT);

def prepareDecklistsDirectory():
	# create decklist directory, if necessary, and let the user know that nothing will happen until they fill it with decklists
	if not os.path.isdir(DECKLIST_DIRECTORY_ROOT):
		os.mkdir(DECKLIST_DIRECTORY_ROOT);
		raise Exception("Decklist directory doesn't exist! Creating it.  Fill with %s decklists to start downloading images." % DECKLIST_SUFFIX)

def prepareDoubleFacedCardFile():
	# go through double-faced card dictionary, which gets appended to over time as double-faced cards are downloaded
	if not os.path.isfile(DOUBLE_FACED_CARD_DICTIONARY_PATH):
		open(DOUBLE_FACED_CARD_DICTIONARY_PATH, 'w').close()

def populateDoubleFacedCardDict():
	doubleFacedCardDict = {}
	with open(DOUBLE_FACED_CARD_DICTIONARY_PATH, 'r+') as doubleFacedCardFile:
		doubleFacedCardFileContents = doubleFacedCardFile.read()
		frontFaceName = None
		for line in doubleFacedCardFileContents.split("\n"):
			if not frontFaceName:
				frontFaceName = line
			else:
				doubleFacedCardDict[frontFaceName] = line
				frontFaceName = None

	return doubleFacedCardDict

def populateExistingImageDict():
	# go through image directory, make dictionary of existing names
	existingImageDict = {}

	for subdir, dirs, files in os.walk(IMAGE_DIRECTORY_ROOT):
		for file in files:
			if file.endswith(IMAGE_SUFFIX):
				existingImageDict[file.lower()] = True

	return existingImageDict

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
		cardName = matches.group(3).strip()

		if cardName:
			decklistDict[cardName] = decklistDict.get(cardName, 0) + cardCount

	addDoubleFacedCardsToDict(decklistDict)
	return decklistDict

def deleteExistingDecklistImages(subDir, files):
	if not RECOPY_IMAGES:
		return

	for fileName in files:
		if fileName.endswith(IMAGE_SUFFIX):
			os.remove(os.path.join(subDir, fileName))

def getFormatNameFromSubDir(subDir):
	subDir = subDir.replace('\\', '/')
	formatNameMatches = re.search("\.\/decklists\/(.*?)(\/|$)", subDir)
	formatName = formatNameMatches.group(1) if formatNameMatches else ""
	return formatName

def canSkipCardImageDownload(imageNameToCheck, files, existingImageDict):
	if imageNameToCheck in files:
		#print "%s found in directory, skipping" % cardName
		return True

	# check if file already exists in image directory
	if existingImageDict.get(imageNameToCheck.lower(), False):
		#print "%s found in magic images directory, continuing" % cardName
		return True

	return False

def copyCardImagesToDecklistDirectory(decklistDict, existingImageDict, subDir, files, formatName):
	# iterate through dictionary again, copying over as many copies as the decklist specifies
	for initialCardName, cardCount in decklistDict.items():
		cardName = fixCardName(initialCardName, formatName)
		imageNameToCheck = cardName + IMAGE_SUFFIX

		if canSkipCardImageDownload(imageNameToCheck, files, existingImageDict):
			pass # format-specific art exists
		elif USE_FORMAT_SPECIFIC_LANDS and initialCardName in BASIC_LAND_NAMES:
			print("Couldn't find '%s' in the magic images folder or existing images dict.  Using the default %s instead" % (cardName, initialCardName))
			cardName = initialCardName
			imageNameToCheck = cardName + IMAGE_SUFFIX

		if not unfoundCardDict.get(imageNameToCheck, False):
			suffixNum = 1
			while suffixNum <= cardCount:
				oldImagePath = os.path.join(IMAGE_DIRECTORY_ROOT, cardName + IMAGE_SUFFIX)
				newImagePath = os.path.join(subDir, formatName + "_" + cardName + "_" + str(suffixNum) + IMAGE_SUFFIX)
				shutil.copy(oldImagePath, newImagePath)
				suffixNum += 1

def copyCardImagesToDecklistDirectoryMPCFill(decklistDict, existingImageDict, subDir, files, formatName):
	# iterate through dictionary again, copying over as many copies as the decklist specifies
	for initialCardName, cardCount in decklistDict.items():
		cardName = fixCardName(initialCardName, formatName)
		imageNameToCheck = cardName + IMAGE_SUFFIX

		if canSkipCardImageDownload(imageNameToCheck, files, existingImageDict):
			pass # format-specific art exists
		elif USE_FORMAT_SPECIFIC_LANDS and initialCardName in BASIC_LAND_NAMES:
			print("Couldn't find '%s' in the magic images folder or existing images dict.  Using the default %s instead" % (cardName, initialCardName))
			cardName = initialCardName
			imageNameToCheck = cardName + IMAGE_SUFFIX

		if not unfoundCardDict.get(imageNameToCheck, False):
			oldImagePath = os.path.join(IMAGE_DIRECTORY_ROOT, cardName + IMAGE_SUFFIX)
			newImagePath = os.path.join(subDir, cardName + IMAGE_SUFFIX)
			reprocessImageForMPCFill(oldImagePath, newImagePath)

def downloadSingleCardImage(cardName, doubleFacedCardDict, existingImageDict):
	#print("Download single card image -- cardName = %s" % (cardName))
	downloadSuccess = False
	needToRerunLoop = False

	sanitized_cardname, set_code = getUrlSanitizedCardnameAndSet(cardName)
	url = URL_PREFIX + sanitized_cardname + URL_SUFFIX
	print("Checking URL %s" % url)
	response = urllib.request.urlopen(url)
	webContent = str(response.read())
	#print("webContent = %s" % webContent)
	lines = webContent.split("\\n")
	#print("Split downloaded webcontent into %d lines" % len(lines))
	for lineIndex in range(len(lines)):
		if downloadSuccess:
			continue

		line = lines[lineIndex]
		# Example lines
		#          <img class="card a25 border-black" alt="" title="Savannah Lions (A25)" src="https://img.scryfall.com/cards/large/en/a25/33.jpg?1521724798" />
		#          <img class="card isd border-black" alt="" title="Delver of Secrets // Insectile Aberration (ISD)" data-rotate="flip-backside" src="https://img.scryfall.com/cards/large/front/1/1/11bf83bb-c95b-4b4f-9a56-ce7a1816307a.jpg?1545407245" />
		#          <img class="card uma border-black" alt="" title="Fire // Ice (UMA)" data-rotate="rotate-90cw" src="https://img.scryfall.com/cards/large/front/3/f/3f822331-315e-4297-bb69-f1069032c6c5.jpg?1547518354" />
		matches = re.search(IMAGE_IN_SOURCE_REGEX, line)

		cardTitle = None
		isWeirdCardType = None
		weirdCardType = None
		imgUrl = None
		if matches:
			shortSetCode = matches.group(1).upper()
			cardTitle = matches.group(2)
			cardSet = matches.group(3)
			isWeirdCardType = matches.group(4)
			weirdCardType = matches.group(5)
			imgUrl = matches.group(6)

			imgUrlLastChar = imgUrl[-5]
			backInImgUrl = "back" in imgUrl
			isBackImage = imgUrlLastChar == 'b' or backInImgUrl # this feels fragile, but such is the fate of screen scraping

			print("\ncardName = %s\ncardTitle = %s\ncardSet = %s\nshortSetCode = %s\nisWeirdCardType = %s\nweirdCardType = %s\nline = %s\nimgUrl = %s\nimgUrlLastChar = %s\nbackInImgUrl = %s\nisBackImage = %s\n" % (cardName, cardTitle, cardSet, shortSetCode, isWeirdCardType, weirdCardType, line, imgUrl, imgUrlLastChar, backInImgUrl, isBackImage))

			incorrect_double_faced_side = (isDoubleFacedFrontFace(doubleFacedCardDict, cardName) and isBackImage) or (isDoubleFacedBackFace(doubleFacedCardDict, cardName) and not isBackImage)
			incorrect_set_code = (set_code and shortSetCode != set_code)
			ignore_this_set = shortSetCode in CARD_SETS_TO_IGNORE and not set_code
			
			skip_download = incorrect_double_faced_side or incorrect_set_code or ignore_this_set

			if skip_download:
				pass # if-statement was more readable this way
			else:
				# NORMAL (low res) imgUrl: https://cards.scryfall.io/normal/front/b/0/b0faa7f2-b547-42c4-a810-839da50dadfe.jpg?1559591477
				# PNG (high res) imgUrl:   https://cards.scryfall.io/png/front/b/0/b0faa7f2-b547-42c4-a810-839da50dadfe.png?1559591477
				imgUrl = imgUrl.replace("https://cards.scryfall.io/normal", "https://cards.scryfall.io/png")
				imgUrl = imgUrl.replace(".jpg", ".png")
				print("Downloading %s" % imgUrl)
				imgRequest = urllib.request.Request(imgUrl, headers=headers)
				imgData = urllib.request.urlopen(imgRequest).read()

				# save in main image directory, then copy over
				newCardImageFileName = cardName + IMAGE_SUFFIX
				outputImage = open(os.path.join(IMAGE_DIRECTORY_ROOT, newCardImageFileName), 'a+b')
				outputImage.write(imgData)
				outputImage.close()
				existingImageDict[newCardImageFileName.lower()] = True
				downloadSuccess = True
				#print("Download success")

		doubleFaced = weirdCardType == "flip-backside"

		# If we find a double-faced card that we previously didn't know about, add it to the dictionary
		if(doubleFaced and (not isPartOfDoubleFacedCardDict(doubleFacedCardDict, cardName))):
			print("Found a double faced card '%s' that isn't part of the double faced card dictionary. Re-running download loop with updated decklist" % cardName)
			# Delver of Secrets // Insectile Aberration (ISD)
			cardTitleMatches = re.search(".*// (.*)", cardTitle)
			backFaceName = cardTitleMatches.group(1)
			#print("Back face name %s" % backFaceName)

			if backFaceName:
				if(set_code):
					backFaceName = backFaceName + "(" + set_code + ")"

				with open(DOUBLE_FACED_CARD_DICTIONARY_PATH, 'a+') as doubleFacedCardFile:
					doubleFacedCardFile.write(cardName + "\n")
					doubleFacedCardFile.write(backFaceName + "\n")
				doubleFacedCardDict[cardName] = backFaceName
				needToRerunLoop = True
			else:
				raise Exception("Unable to parse back face name from: '%s' " % cardTitle)

	#print("At end of downloadSingleCardImage.  Download success? %s  Need to rerun loop (new double-faced cards found)? %s" % (downloadSuccess, needToRerunLoop))
	return downloadSuccess, needToRerunLoop

def downloadMissingCardImages(decklistDict, unfoundCardDict):
	needToRerunLoop = False

	for initialCardName, cardCount in decklistDict.items():
		# print "%s: %s" % (cardName, cardCount)

		# check if file already exists in current directory
		cardName = fixCardName(initialCardName, formatName)
		#print("Fixed cardName %s" % cardName)

		imageNameToCheck = cardName + IMAGE_SUFFIX
		if canSkipCardImageDownload(imageNameToCheck, files, existingImageDict):
			continue

		if USE_FORMAT_SPECIFIC_LANDS and initialCardName in BASIC_LAND_NAMES:
			print("Couldn't find '%s' in the magic images folder or existing images dict.  If you want a format-specific land, you'll have to create it manually.  Using the default %s instead" % (cardName, initialCardName))
			cardName = initialCardName

			imageNameToCheck = cardName + IMAGE_SUFFIX
			if canSkipCardImageDownload(imageNameToCheck, files, existingImageDict):
				continue

		# try to download from magiccards.info to image directory
		print("%s not downloaded, trying to download from scryfall" % cardName)

		downloadSuccess, needToRerunForThisCard = downloadSingleCardImage(cardName, doubleFacedCardDict, existingImageDict)
		if needToRerunForThisCard:
			needToRerunLoop = True

		if not downloadSuccess:
			unfoundCardDict[imageNameToCheck] = os.path.join(subDir, fileName)
			print("Couldn't download '%s', most likely the card name is mispelled or missing a comma" % cardName)
			# raise Exception("Couldn't find card: '%s' " % imageNameToCheck)

	#print("At end of downloadMissingCardImages.  Need to rerun loop (new double-faced cards found)? %s" % needToRerunLoop)
	return needToRerunLoop

# main
prepareMagicImagesDirectory()
prepareDecklistsDirectory()
prepareDoubleFacedCardFile()

doubleFacedCardDict = populateDoubleFacedCardDict()
existingImageDict = populateExistingImageDict()
unfoundCardDict = {}

# recursively go through decklists directory, looking for txt files
for subDir, dirs, files in os.walk(DECKLIST_DIRECTORY_ROOT):
	deleteExistingDecklistImages(subDir, files)
	formatName = getFormatNameFromSubDir(subDir)

	for fileName in files:
		#if a txt file is found
		if fileName.endswith(DECKLIST_SUFFIX):
			runLoop = True
			while(runLoop):
				decklistDict = populateInitialDecklistDict(subDir, fileName)
				runLoop = downloadMissingCardImages(decklistDict, unfoundCardDict)

			if DO_MPCFILL_POSTPROCESSING:
				copyCardImagesToDecklistDirectoryMPCFill(decklistDict, existingImageDict, subDir, files, formatName)
			else:
				copyCardImagesToDecklistDirectory(decklistDict, existingImageDict, subDir, files, formatName)

# print out unfound cards
if len(unfoundCardDict) == 0:
	print("*******************************************************")
	print("*********** SUCCESS! No unfound card names! ***********")
	print("*******************************************************")
else:
	for cardName, decklistName in unfoundCardDict.items():
		print("Couldn't find cardname '%s' in decklist '%s'" % (cardName, decklistName))