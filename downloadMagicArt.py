#http://magiccards.info/query?q=%21bayou&v=card&s=cname
import os
import re
import shutil
import urllib2

urlPrefix = "https://scryfall.com/search?q=!%27";
urlSuffix = "%27&v=card&s=cname";

magicCardsDotInfoPrefix = "https://magiccards.info"

imgSuffix = ".jpg"

imageDirectoryRoot = "./magic_images"
decklistDirectoryRoot = "./decklists"

RECOPY_IMAGES = True

# urllib2 junk
user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
headers = { 'User-Agent' : user_agent }

doubleFacedCardDict = {
	"Delver of Secrets": "Insectile Aberration",
	"Jace, Vryn's Prodigy": "Jace, Telepath Unbound",
	"Duskwatch Recruiter": "Krallenhorde Howler",
	"Kytheon, Hero of Akros": "Gideon, Battle-Forged",
	"Nissa, Vastwood Seer": "Nissa, Sage Animist",
	"Huntmaster of the Fells": "Ravager of the Fells",
	"Search for Azcanta": "Azcanta, The Sunken Ruin",
	"Garruk Relentless": "Garruk, the Veil-Cursed",
	"Arlinn Kord": "Arlinn, Embraced By the Moon",
	"Ulrich of the Krallenhorde": "Ulrich, Uncontested Alpha",
	"Legion's Landing": "Adanto, the First Fort",
	"Brian Wong": "Brian Wong's Giant Ego",
	"Gisela, the Broken Blade": "Brisela, Voice of Nightmares",
	"Arguel's Blood Fast": "Temple of Aclazotz",
}

ignoreSplitCardName = [ "Show and Tell", "Tooth and Nail" ]
doubleFaceCardNamesToIgnore = [ "Jushi Apprentice" ]

cardNamesToIgnore = [ "n/a" ]

basicLandNames = ["Forest", "Island", "Mountain", "Plains", "Swamp"]

def ignoreDoubleFaceCardName(cardName):
	return cardName in doubleFaceCardNamesToIgnore

def shouldIgnoreCardName(cardName):
	if not cardName:
		return True

	if cardName.lower() in cardNamesToIgnore:
		return True

def isPartOfDoubleFacedCardDict(cardName):
	for frontName, backName in doubleFacedCardDict.iteritems():
		if frontName == cardName or backName == cardName:
			return True

	return False

def isDoubleFacedFrontFace(cardName):
	for frontName, backName in doubleFacedCardDict.iteritems():
		if frontName == cardName:
			return True

	return False

def isDoubleFacedBackFace(cardName):
	for frontName, backName in doubleFacedCardDict.iteritems():
		if backName == cardName:
			return True

	return False

def isSplitCard(cardName):
	if cardName in ignoreSplitCardName:
		return False

	return re.search("^(\S*?) and (\S*)", cardName)

def fixCardName(cardName, formatName):
	splitCardName = re.search("^(\S*?)\s*\/\/?\s*(\S*)", cardName)
	if splitCardName:
		newCardName = splitCardName.group(1).capitalize() + " and " + splitCardName.group(2).capitalize()
		return newCardName

	if cardName in basicLandNames:
		cardName = cardName + formatName

	return cardName

def getUrlSanitizedCardname(cardName):
	splitCard = isSplitCard(cardName)
	if splitCard:
		# 'Rough and Tumble' becomes 'Rough (Rough/Tumble)'
		convertedSplitCardName = splitCard.group(1) + " (" + splitCard.group(1) + "/" + splitCard.group(2) + ")"
		print("Converting split card name '%s' into '%s'" % (cardName, convertedSplitCardName))
		cardName = convertedSplitCardName

	# https://www.degraeve.com/reference/specialcharacters.php
	cardName = cardName.replace("'", "")
	cardName = cardName.replace("(", "%28")
	cardName = cardName.replace(")", "%29")
	cardName = cardName.replace("!", "%33")
	cardName = cardName.replace("\"", "%34")
	cardName = cardName.replace(":", "%3A")
	cardName = cardName.replace(" ", "+")
	return cardName

def addDoubleFacedCardsToDict(decklistDict):
	cardsToAdd = {}
	for cardName, cardCount in decklistDict.iteritems():
		otherFaceCardName = doubleFacedCardDict.get(cardName, None)
		if otherFaceCardName != None:
			cardsToAdd[otherFaceCardName] = cardCount

	for cardName, cardCount in cardsToAdd.iteritems():
		decklistDict[cardName] = cardCount

if not os.path.isdir(imageDirectoryRoot):
	os.mkdir(imageDirectoryRoot);

if not os.path.isdir(decklistDirectoryRoot):
	os.mkdir(decklistDirectoryRoot);
	raise Exception("Decklist directory doesn't exist! Creating it.  Fill with .txt decklists to start downloading images.")

# go through image directory, make dictionary of existing names
existingImageDictionary = {}
for subdir, dirs, files in os.walk(imageDirectoryRoot):
	for file in files:
		if file.endswith(imgSuffix):
			#print file[:-4]
			existingImageDictionary[file.lower()] = True

unfoundCardDict = {}
# recursively go through decklists directory, looking for txt files
for subdir, dirs, files in os.walk(decklistDirectoryRoot):
	if RECOPY_IMAGES:
		for fileName in files:
			if fileName.endswith(imgSuffix):
				os.remove(os.path.join(subdir, fileName))

	formatNameMatches = re.search("\.\/decklists\/(.*?)(\/|$)", subdir)
	formatName = formatNameMatches.group(1) if formatNameMatches else ""

	for fileName in files:
		#if a txt file is found
		if fileName.endswith(".txt"):
			# load it and cram into dictionary
			decklistDict = {}
			fileContents = open(os.path.join(subdir, fileName), 'r').read()
			for line in fileContents.split("\n"):
				matches = re.search("(\d*)x?(\s*)(.*)", line)
				cardCount = 1 if matches.group(1) == '' else int(matches.group(1))
				cardName = matches.group(3)
				decklistDict[cardName] = decklistDict.get(cardName, 0) + cardCount

			addDoubleFacedCardsToDict(decklistDict)
			# iterate through dictionary
			for cardName, cardCount in decklistDict.iteritems():
				# print "%s: %s" % (cardName, cardCount)
				# check if file already exists in current directory
				if shouldIgnoreCardName(cardName):
					continue

				cardName = fixCardName(cardName, formatName)

				imageNameToCheck = cardName + imgSuffix
				if imageNameToCheck in files:
					#print "%s found in directory, skipping" % cardName
					continue

				# check if file already exists in image directory
				if existingImageDictionary.get(imageNameToCheck.lower(), False):
					#print "%s found in magic images directory, continuing" % cardName
					continue

				# try to download from magiccards.info to image directory
				print "%s not downloaded, trying to download from scryfall" % cardName
				downloadSuccess = False
				url = urlPrefix + getUrlSanitizedCardname(cardName) + urlSuffix
				#print("Checking URL %s" % url)
				response = urllib2.urlopen(url)
				webContent = response.read()
				#print("webContent = %s" % webContent)
				lines = webContent.split("\n")
				for lineIndex in range(len(lines)):
					line = lines[lineIndex]
					#      <img class="card bng border-black" alt="" title="Eidolon of Countless Battles (BNG)" src="https://img.scryfall.com/cards/large/en/bng/7.jpg?1517813031" />
					matches = None
					if isDoubleFacedFrontFace(cardName):
						matches = re.search("\s*<img class.*src=\"(.*a\.jpg).*", line)
					elif isDoubleFacedBackFace(cardName):
						matches = re.search("\s*<img class.*src=\"(.*b\.jpg).*", line)
					else:
						matches = re.search("\s*<img class.*src=\"(.*\.jpg).*", line)

					imgUrl = None
					if matches:
						imgUrl = matches.group(1)
						#print("line = ", line)
						#print("imgUrl = ", imgUrl)

						imgRequest = urllib2.Request(imgUrl, headers=headers)
						imgData = urllib2.urlopen(imgRequest).read()

						# save in main image directory, then copy over
						outputImage = open(os.path.join(imageDirectoryRoot, imageNameToCheck), 'a')
						outputImage.write(imgData)
						outputImage.close()
						downloadSuccess = True

					doubleFaced = imgUrl and (imgUrl[-5] == 'a' or imgUrl[-5] == 'b')
					#if doubleFaced:
					#	print("%s is double faced! is split card? %s, ignoreDoubleFaceCardName? %s, isPartOfDoubleFacedCardDict? %s" % (doubleFaced, isSplitCard(cardName), ignoreDoubleFaceCardName(cardName), isPartOfDoubleFacedCardDict(cardName)))
					if(doubleFaced and (not isSplitCard(cardName)) and (not ignoreDoubleFaceCardName(cardName)) and (not isPartOfDoubleFacedCardDict(cardName))):
						os.remove(os.path.join(imageDirectoryRoot, imageNameToCheck))
						try:
							os.remove(os.path.join(subdir, imageNameToCheck))
						except:
							pass
						otherFaceLine = lines[lineIndex+3]
						#         <a href="/xln/en/22b.html">Adanto, the First Fort</a><br><br>
						otherFaceMatches = re.search("\s*<a href.*>(.*)<\/a>.*", otherFaceLine)
						otherFaceMatch = "NOT FOUND"
						if otherFaceMatches:
							otherFaceMatch = otherFaceMatches.group(1)
						preparedLine = "\"%s\": \"%s\"," % (cardName, otherFaceMatch)
						raise Exception("Found a double faced card '%s' that isn't part of the double faced card dictionary.  Add it and re-run. Try:\n%s" % (cardName, preparedLine))
			
				if not downloadSuccess:
					unfoundCardDict[imageNameToCheck] = fileName
					print("Couldn't download '%s', most likely the card name is mispelled or missing a comma" % cardName)
					# raise Exception("Couldn't find card: '%s' " % imageNameToCheck)

			# iterate through dictionary again, looking at card counts
			for cardName, cardCount in decklistDict.iteritems():
				if shouldIgnoreCardName(cardName):
					continue

				cardName = fixCardName(cardName, formatName)

				if not unfoundCardDict.get(cardName + imgSuffix, False):
					suffixNum = 1
					while suffixNum <= cardCount:
						shutil.copy(os.path.join(imageDirectoryRoot, cardName + imgSuffix), os.path.join(subdir, cardName + "_" + str(suffixNum) + imgSuffix))
						suffixNum += 1

# print out unfound cards
if len(unfoundCardDict) == 0:
	print("*******************************************************")
	print("*********** SUCCESS! No unfound card names! ***********")
	print("*******************************************************")
else:
	for cardName, decklistName in unfoundCardDict.iteritems():
		print("Couldn't find cardname '%s' in decklist '%s'" % (cardName, decklistName))

