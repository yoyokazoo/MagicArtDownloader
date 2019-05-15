import os
import re
import shutil

import urllib.request
import string

urlPrefix = "https://scryfall.com/search?q=!%27";
urlSuffix = "%27&v=card&s=cname";
IMAGE_SUFFIX = ".jpg"
DECKLIST_SUFFIX = ".txt"

doubleFacedCardDictionaryPath =  "./doubleFacedCardDict.txt"
imageDirectoryRoot = "./magic_images"
decklistDirectoryRoot = "./decklists"


RECOPY_IMAGES = True
USE_FORMAT_SPECIFIC_LANDS = True

# urllib2 junk
user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
headers = { 'User-Agent' : user_agent }



BASIC_LAND_NAMES = ["Forest", "Island", "Mountain", "Plains", "Swamp"]

def ignoreDoubleFaceCardName(cardName):
	return cardName in doubleFaceCardNamesToIgnore

def shouldIgnoreCardName(cardName):
	if not cardName:
		return True

	if cardName.lower() in cardNamesToIgnore:
		return True

def isPartOfDoubleFacedCardDict(cardName):
	for frontName, backName in doubleFacedCardDict.items():
		if frontName == cardName or backName == cardName:
			return True

	return False

def isDoubleFacedFrontFace(cardName):
	for frontName, backName in doubleFacedCardDict.items():
		if frontName == cardName:
			return True

	return False

def isDoubleFacedBackFace(cardName):
	for frontName, backName in doubleFacedCardDict.items():
		if backName == cardName:
			return True

	return False

def fixCardName(cardName, formatName):
	# Convert Fire / Ice, Fire//Ice into Fire_Ice
	splitCardName = re.search("^(\S*?)\s*\/\/?\s*(\S*)", cardName)
	if splitCardName:
		newCardName = splitCardName.group(1).capitalize() + "_" + splitCardName.group(2).capitalize()
		return newCardName

	# Convert Plains into PlainsModern, PlainsStandard, PlainsTestCard etc.
	# so you can associate different basic land arts with different decklists
	#print("Card name: %s Format name: %s" % (cardName, formatName))
	if USE_FORMAT_SPECIFIC_LANDS and cardName in BASIC_LAND_NAMES:
		cardName = cardName + formatName

	return cardName

def getUrlSanitizedCardname(cardName):
	# https://www.degraeve.com/reference/specialcharacters.php
	cardName = cardName.replace("'", "")
	cardName = cardName.replace("(", "%28")
	cardName = cardName.replace(")", "%29")
	cardName = cardName.replace("!", "%33")
	cardName = cardName.replace("\"", "%34")
	cardName = cardName.replace(":", "%3A")
	cardName = cardName.replace(" ", "+")
	cardName = cardName.replace("_", "//") # change Fire_Ice to Fire//Ice
	return cardName

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
	if not os.path.isdir(imageDirectoryRoot):
		os.mkdir(imageDirectoryRoot);

def prepareDecklistsDirectory():
	# create decklist directory, if necessary, and let the user know that nothing will happen until they fill it with decklists
	if not os.path.isdir(decklistDirectoryRoot):
		os.mkdir(decklistDirectoryRoot);
		raise Exception("Decklist directory doesn't exist! Creating it.  Fill with %s decklists to start downloading images." % DECKLIST_SUFFIX)

def prepareDoubleFacedCardFile():
	# go through double-faced card dictionary, which gets appended to over time as double-faced cards are downloaded
	if not os.path.isfile(doubleFacedCardDictionaryPath):
		open(doubleFacedCardDictionaryPath, 'w').close()

def populateDoubleFacedCardDict():
	doubleFacedCardDict = {}
	with open(doubleFacedCardDictionaryPath, 'r+') as doubleFacedCardFile:
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

	for subdir, dirs, files in os.walk(imageDirectoryRoot):
		for file in files:
			if file.endswith(IMAGE_SUFFIX):
				existingImageDict[file.lower()] = True

	return existingImageDict

def populateInitialDecklistDict(subDir, fileName):
	# load it and cram into dictionary
	decklistDict = {}
	fileContents = open(os.path.join(subDir, fileName), 'r').read()
	for line in fileContents.split("\n"):
		matches = re.search("(\d*)x?(\s*)(.*)", line)
		cardCount = 1 if matches.group(1) == '' else int(matches.group(1))
		cardName = matches.group(3)

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

# main
prepareMagicImagesDirectory()
prepareDecklistsDirectory()
prepareDoubleFacedCardFile()

doubleFacedCardDict = populateDoubleFacedCardDict()
existingImageDict = populateExistingImageDict()

unfoundCardDict = {}

decklistDict = {}

#print(doubleFacedCardDict)


# recursively go through decklists directory, looking for txt files
for subDir, dirs, files in os.walk(decklistDirectoryRoot):
	deleteExistingDecklistImages(subDir, files)
	formatName = getFormatNameFromSubDir(subDir)

	for fileName in files:
		#if a txt file is found
		if fileName.endswith(DECKLIST_SUFFIX):
			decklistDict = populateInitialDecklistDict(subDir, fileName)
			# iterate through dictionary
			rerunLoop = True
			while(rerunLoop):
				rerunLoop = False

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
					downloadSuccess = False
					url = urlPrefix + getUrlSanitizedCardname(cardName) + urlSuffix
					#print("Checking URL %s" % url)
					response = urllib.request.urlopen(url)
					webContent = str(response.read())
					#print("webContent = %s" % webContent)
					lines = webContent.split("\\n")
					#print("Split downloaded webcontent into %d lines" % len(lines))
					for lineIndex in range(len(lines)):
						line = lines[lineIndex]
						# Example lines
						#          <img class="card a25 border-black" alt="" title="Savannah Lions (A25)" src="https://img.scryfall.com/cards/large/en/a25/33.jpg?1521724798" />
						#          <img class="card isd border-black" alt="" title="Delver of Secrets // Insectile Aberration (ISD)" data-rotate="flip-backside" src="https://img.scryfall.com/cards/large/front/1/1/11bf83bb-c95b-4b4f-9a56-ce7a1816307a.jpg?1545407245" />
						#          <img class="card uma border-black" alt="" title="Fire // Ice (UMA)" data-rotate="rotate-90cw" src="https://img.scryfall.com/cards/large/front/3/f/3f822331-315e-4297-bb69-f1069032c6c5.jpg?1547518354" />
						matches = re.search("\s*<img class.*title=\"(.*?)\".*?(data-rotate=\"(.*?)\" )?src=\"(.*\.jpg).*", line)

						cardTitle = None
						isWeirdCardType = None
						weirdCardType = None
						imgUrl = None
						if matches:
							cardTitle = matches.group(1)
							isWeirdCardType = matches.group(2)
							weirdCardType = matches.group(3)
							imgUrl = matches.group(4)

							imgUrlLastChar = imgUrl[-5]
							backInImgUrl = "back" in imgUrl
							isBackImage = imgUrlLastChar == 'b' or backInImgUrl # this feels fragile, but such is the fate of screen scraping

							#print("\ncardName = %s\ncardTitle = %s\nisWeirdCardType = %s\nweirdCardType = %s\nline = %s\nimgUrl = %s\nimgUrlLastChar = %s\nbackInImgUrl = %s\nisBackImage = %s\n" % (cardName, cardTitle, isWeirdCardType, weirdCardType, line, imgUrl, imgUrlLastChar, backInImgUrl, isBackImage))

							if (isDoubleFacedFrontFace(cardName) and isBackImage) or (isDoubleFacedBackFace(cardName) and not isBackImage):
								pass # if-statement was more readable this way
							else:
								imgRequest = urllib.request.Request(imgUrl, headers=headers)
								imgData = urllib.request.urlopen(imgRequest).read()

								# save in main image directory, then copy over
								outputImage = open(os.path.join(imageDirectoryRoot, imageNameToCheck), 'a+b')
								outputImage.write(imgData)
								outputImage.close()
								downloadSuccess = True

						doubleFaced = weirdCardType == "flip-backside"

						# If we find a double-faced card that we previously didn't know about, add it to the dictionary
						if(doubleFaced and (not isPartOfDoubleFacedCardDict(cardName))):
							print("Found a double faced card '%s' that isn't part of the double faced card dictionary." % cardName)
							# Delver of Secrets // Insectile Aberration (ISD)
							cardTitleMatches = re.search(".*// (.*) \(...\)", cardTitle)
							backFaceName = cardTitleMatches.group(1)
							print("Back face name %s" % backFaceName)

							if backFaceName:
								with open(doubleFacedCardDictionaryPath, 'a+') as doubleFacedCardFile:
									doubleFacedCardFile.write(cardName + "\n")
									doubleFacedCardFile.write(backFaceName + "\n")
								doubleFacedCardDict[cardName] = backFaceName
								rerunLoop = True
							else:
								raise Exception("Unable to parse back face name from: '%s' " % cardTitle)
				
					if not downloadSuccess:
						unfoundCardDict[imageNameToCheck] = fileName
						print("Couldn't download '%s', most likely the card name is mispelled or missing a comma" % cardName)
						# raise Exception("Couldn't find card: '%s' " % imageNameToCheck)


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
						shutil.copy(os.path.join(imageDirectoryRoot, cardName + IMAGE_SUFFIX), os.path.join(subDir, cardName + "_" + str(suffixNum) + IMAGE_SUFFIX))
						suffixNum += 1

# print out unfound cards
if len(unfoundCardDict) == 0:
	print("*******************************************************")
	print("*********** SUCCESS! No unfound card names! ***********")
	print("*******************************************************")
else:
	for cardName, decklistName in unfoundCardDict.items():
		print("Couldn't find cardname '%s' in decklist '%s'" % (cardName, decklistName))

