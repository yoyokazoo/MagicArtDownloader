import os
import re
import shutil

import urllib.request
import urllib.parse
import json
import time
import string

# pip install pillow
from PIL import Image


import xml.etree.ElementTree as ET

SCRYFALL_API_SEARCH = "https://api.scryfall.com/cards/search"

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

MAINDECK_REGEX = r"\s*[mM]ain\s*[dD]eck:?\s*"
SIDEBOARD_REGEX = r"\s*[sS]ide\s*[bB]oard:?\s*"

SET_CODE_REGEX = r"(\s*\(([A-Z0-9]{2,6})\))$"


RECOPY_IMAGES = True
# todo: if format-specific land doesn't exist, just download the base version and make a copy with the format-specific version
USE_FORMAT_SPECIFIC_LANDS = True
DO_MPCFILL_POSTPROCESSING = True

headers = {'User-Agent': 'MagicArtDownloader/1.0', 'Accept': 'application/json'}

BASIC_LAND_NAMES = ["Forest", "Island", "Mountain", "Plains", "Swamp"]

MPC_FILL_BRACKETS = [18, 36, 55, 72, 90, 108, 126, 144, 162, 180, 198, 216, 234, 396, 504, 612]
MPC_FILL_CARDBACK = "1lZX4vyveCm_h-bAzvvgK1d-T60dG-OtJ"
MPC_FILL_PLACEHOLDER_ID = "1Cw1NnGISzJPWL-PrhgpexiuIdPhHiasc"

def getMPCFillBracket(quantity):
	for bracket in MPC_FILL_BRACKETS:
		if bracket > quantity:
			return bracket

	print("*******************************************************")
	print("*** ERROR: Card quantity exceeded max bracket size ****")
	print("*******************************************************")

	return bracket[-1]

def createXMLFileForMPCFill(decklistDict, existingImageDict, subDir, files, formatName):

	frontDecklistDict = {}
	for card_name, card_count in decklistDict.items():
		if not isDoubleFacedBackFace(doubleFacedCardDict, card_name):
			frontDecklistDict[card_name] = card_count

	# Create the root element
	root = ET.Element("order")

	cardCountTotal = sum(frontDecklistDict.values())

	details = ET.Element("details")
	quantity = ET.Element("quantity")
	bracket = ET.Element("bracket")
	stock = ET.Element("stock")
	foil = ET.Element("foil")

	quantity.text = str(cardCountTotal)
	bracket.text = str(getMPCFillBracket(cardCountTotal))
	stock.text = "(S30) Standard Smooth"
	foil.text = "false"

	details.append(quantity)
	details.append(bracket)
	details.append(stock)
	details.append(foil)

	root.append(details)

	# Iterate over the dictionary
	fronts = ET.Element("fronts")
	backs = ET.Element("backs")
	runningOffset = 0
	for card_name, card_count in frontDecklistDict.items():
		# Create the <card> element
		card_element = ET.Element("card")

		# Just give it a nonsense id so I don't have to make changes to the uploader
		id_element = ET.Element("id")
		id_element.text = MPC_FILL_PLACEHOLDER_ID

		# Create the <slots> element and set its text
		slots_element = ET.Element("slots")
		slots = ",".join(str(i) for i in range(runningOffset, runningOffset + card_count))
		slots_element.text = slots

		# Create the <name> element and set its text
		name_element = ET.Element("name")
		name_element.text = fixCardName(card_name, formatName) + IMAGE_SUFFIX

		runningOffset += card_count

		if isDoubleFacedFrontFace(doubleFacedCardDict, card_name):
			back_card_element = ET.Element("card")
			back_id_element = ET.Element("id")
			back_slots_element = ET.Element("slots")
			back_name_element = ET.Element("name")

			back_id_element.text = MPC_FILL_PLACEHOLDER_ID
			back_name_element.text = fixCardName(doubleFacedCardDict[card_name], formatName) + IMAGE_SUFFIX
			back_slots_element.text = slots
			
			back_card_element.append(back_id_element)
			back_card_element.append(slots_element)
			back_card_element.append(back_name_element)
			
			backs.append(back_card_element)

		# Add the <slots> and <name> elements to the <card> element
		card_element.append(id_element)
		card_element.append(slots_element)
		card_element.append(name_element)

		# Add the <card> element to the root element
		fronts.append(card_element)

	root.append(fronts)

	if len(backs) > 0:
		root.append(backs)

	cardbacks = ET.Element("cardback")
	cardbacks.text = MPC_FILL_CARDBACK

	root.append(cardbacks)

	# Create an ElementTree object
	tree = ET.ElementTree(root)

	# Write the XML to a file
	tree.write("output.xml")

def sample_border_colors(image):
	# Thanks ChatGPT, I'm lazy!
    # Define the region to sample (excluding the rounded corners)
    left = 25
    top = 25
    right = image.width - 25
    bottom = image.height - 25
    sample_region = [(x, top) for x in range(left, right)] + \
                    [(right, y) for y in range(top, bottom)] + \
                    [(x, bottom) for x in range(right, left, -1)] + \
                    [(left, y) for y in range(bottom, top, -1)]

    # Sample 20 pixels from the border
    pixels = [image.getpixel(coord) for coord in sample_region[:20]]

    # Calculate the average color
    total_r = sum(rgb[0] for rgb in pixels)
    total_g = sum(rgb[1] for rgb in pixels)
    total_b = sum(rgb[2] for rgb in pixels)
    avg_r = total_r // len(pixels)
    avg_g = total_g // len(pixels)
    avg_b = total_b // len(pixels)

    return (avg_r, avg_g, avg_b)

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
	average_border_color = sample_border_colors(original_image)
	new_image = Image.new('RGB', (816, 1110), average_border_color)

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
	splitCardName = re.search(r"^(\S*?)\s*\/\/?\s*(\S*)", cardName)
	if splitCardName:
		newCardName = splitCardName.group(1).capitalize() + "_" + splitCardName.group(2).capitalize()
		cardName = newCardName # should be cardName = newCardName so we can fix all screwups?

	# Circle of Protection: Blue into Circle of Protection Blue
	colonCardName = re.search(r"([^:]*):\s*([^:]*)", cardName)
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

	return cardName.strip()


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
				frontFaceName = line.strip()
			else:
				doubleFacedCardDict[frontFaceName] = line.strip()
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

		matches = re.search(r"(\d*)x?(\s*)(.*)", line)
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
	formatNameMatches = re.search(r"\.\/decklists\/(.*?)(\/|$)", subDir)
	formatName = formatNameMatches.group(1) if formatNameMatches else ""
	return formatName

def safeFilename(cardName):
	return cardName.replace(" // ", " -- ")

def splitCombinedCardName(cardName):
	if " // " not in cardName:
		return None
	set_code = None
	set_code_match = re.search(SET_CODE_REGEX, cardName)
	if set_code_match:
		set_code = set_code_match.group(2)
		cardName = cardName[:-len(set_code_match.group(1))].strip()
	front, back = cardName.split(" // ", 1)
	if set_code:
		return "%s (%s)" % (front.strip(), set_code), "%s (%s)" % (back.strip(), set_code)
	return front.strip(), back.strip()

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
		combined = splitCombinedCardName(cardName)
		if combined:
			frontName, backName = combined
			for faceName in (frontName, backName):
				if not unfoundCardDict.get(faceName + IMAGE_SUFFIX, False):
					suffixNum = 1
					while suffixNum <= cardCount:
						oldImagePath = os.path.join(IMAGE_DIRECTORY_ROOT, faceName + IMAGE_SUFFIX)
						newImagePath = os.path.join(subDir, formatName + "_" + faceName + "_" + str(suffixNum) + IMAGE_SUFFIX)
						shutil.copy(oldImagePath, newImagePath)
						suffixNum += 1
			continue

		imageNameToCheck = safeFilename(cardName) + IMAGE_SUFFIX

		if canSkipCardImageDownload(imageNameToCheck, files, existingImageDict):
			pass # format-specific art exists
		elif USE_FORMAT_SPECIFIC_LANDS and initialCardName in BASIC_LAND_NAMES:
			print("Couldn't find '%s' in the magic images folder or existing images dict.  Using the default %s instead" % (cardName, initialCardName))
			cardName = initialCardName
			imageNameToCheck = safeFilename(cardName) + IMAGE_SUFFIX

		if not unfoundCardDict.get(imageNameToCheck, False):
			suffixNum = 1
			while suffixNum <= cardCount:
				oldImagePath = os.path.join(IMAGE_DIRECTORY_ROOT, safeFilename(cardName) + IMAGE_SUFFIX)
				newImagePath = os.path.join(subDir, formatName + "_" + safeFilename(cardName) + "_" + str(suffixNum) + IMAGE_SUFFIX)
				shutil.copy(oldImagePath, newImagePath)
				suffixNum += 1

def copyCardImagesToDecklistDirectoryMPCFill(decklistDict, existingImageDict, subDir, files, formatName):
	# iterate through dictionary again, copying over as many copies as the decklist specifies
	for initialCardName, cardCount in decklistDict.items():
		cardName = fixCardName(initialCardName, formatName)
		combined = splitCombinedCardName(cardName)
		if combined:
			frontName, backName = combined
			for faceName in (frontName, backName):
				if not unfoundCardDict.get(faceName + IMAGE_SUFFIX, False):
					oldImagePath = os.path.join(IMAGE_DIRECTORY_ROOT, faceName + IMAGE_SUFFIX)
					newImagePath = os.path.join(subDir, faceName + IMAGE_SUFFIX)
					reprocessImageForMPCFill(oldImagePath, newImagePath)
			continue

		imageNameToCheck = safeFilename(cardName) + IMAGE_SUFFIX

		if canSkipCardImageDownload(imageNameToCheck, files, existingImageDict):
			pass # format-specific art exists
		elif USE_FORMAT_SPECIFIC_LANDS and initialCardName in BASIC_LAND_NAMES:
			print("Couldn't find '%s' in the magic images folder or existing images dict.  Using the default %s instead" % (cardName, initialCardName))
			cardName = initialCardName
			imageNameToCheck = safeFilename(cardName) + IMAGE_SUFFIX

		if not unfoundCardDict.get(imageNameToCheck, False):
			oldImagePath = os.path.join(IMAGE_DIRECTORY_ROOT, safeFilename(cardName) + IMAGE_SUFFIX)
			newImagePath = os.path.join(subDir, safeFilename(cardName) + IMAGE_SUFFIX)
			reprocessImageForMPCFill(oldImagePath, newImagePath)

def downloadSingleCardImage(scryfallName, fileCardName, doubleFacedCardDict, existingImageDict):
	downloadSuccess = False
	needToRerunLoop = False

	# If card name is "Front // Back (SET)", download each face as its own file
	combined = splitCombinedCardName(fileCardName)
	if combined:
		frontName, backName = combined
		frontSuccess, _ = downloadSingleCardImage(frontName, frontName, doubleFacedCardDict, existingImageDict)
		backSuccess, _ = downloadSingleCardImage(backName, backName, doubleFacedCardDict, existingImageDict)
		return frontSuccess and backSuccess, False

	# Extract optional set code (e.g. "Savannah Lions (A25)" → set_code="A25")
	set_code = None
	plain_name = scryfallName
	set_code_match = re.search(SET_CODE_REGEX, scryfallName)
	if set_code_match:
		set_code = set_code_match.group(2)
		plain_name = scryfallName[:-len(set_code_match.group(1))].strip()

	# Normalize mojibake curly apostrophe to a straight apostrophe for Scryfall
	plain_name = plain_name.replace("â€™", "'")

	params = urllib.parse.urlencode({
		'q': '!"%s"' % plain_name,
		'order': 'released',
		'dir': 'asc',
		'unique': 'prints'
	})
	api_url = SCRYFALL_API_SEARCH + "?" + params
	print("Checking URL %s" % api_url)

	try:
		request = urllib.request.Request(api_url, headers=headers)
		response = urllib.request.urlopen(request)
		data = json.loads(response.read())
	except urllib.error.HTTPError as e:
		print("HTTP error fetching '%s': %s" % (scryfallName, e))
		return False, False

	for card in data.get("data", []):
		if downloadSuccess:
			break

		shortSetCode = card["set"].upper()
		doubleFaced = card.get("layout") in ["transform", "modal_dfc"]

		incorrect_set_code = set_code and shortSetCode != set_code
		ignore_this_set = shortSetCode in CARD_SETS_TO_IGNORE and not set_code

		if incorrect_set_code or ignore_this_set:
			continue

		# If this is a newly-encountered double-faced card, record it and signal a re-run
		if doubleFaced and not isPartOfDoubleFacedCardDict(doubleFacedCardDict, fileCardName):
			card_faces = card.get("card_faces", [])
			if len(card_faces) >= 2:
				backFaceName = card_faces[1]["name"]
				print("Found double-faced card '%s', adding to dictionary and re-running" % fileCardName)
				if set_code:
					backFaceName = backFaceName + " (" + set_code + ")"
				with open(DOUBLE_FACED_CARD_DICTIONARY_PATH, 'a+') as f:
					f.write(fileCardName + "\n")
					f.write(backFaceName + "\n")
				doubleFacedCardDict[fileCardName] = backFaceName
				needToRerunLoop = True

		isBackFace = isDoubleFacedBackFace(doubleFacedCardDict, fileCardName)
		if "image_uris" in card:
			imgUrl = card["image_uris"]["png"]
		elif "card_faces" in card:
			face_index = 1 if isBackFace else 0
			imgUrl = card["card_faces"][face_index]["image_uris"]["png"]
		else:
			print("No image URL found for '%s'" % scryfallName)
			continue

		print("Downloading %s" % imgUrl)
		imgRequest = urllib.request.Request(imgUrl, headers=headers)
		imgData = urllib.request.urlopen(imgRequest).read()

		newCardImageFileName = safeFilename(fileCardName) + IMAGE_SUFFIX
		with open(os.path.join(IMAGE_DIRECTORY_ROOT, newCardImageFileName), 'ab') as f:
			f.write(imgData)
		existingImageDict[newCardImageFileName.lower()] = True
		downloadSuccess = True
		time.sleep(0.3)

	return downloadSuccess, needToRerunLoop

def downloadMissingCardImages(decklistDict, unfoundCardDict):
	needToRerunLoop = False

	for initialCardName, cardCount in decklistDict.items():
		# print "%s: %s" % (cardName, cardCount)

		# check if file already exists in current directory
		cardName = fixCardName(initialCardName, formatName)
		#print("Fixed cardName %s" % cardName)

		combined = splitCombinedCardName(cardName)
		if combined:
			frontName, backName = combined
			frontImageName = frontName + IMAGE_SUFFIX
			backImageName = backName + IMAGE_SUFFIX
			if canSkipCardImageDownload(frontImageName, files, existingImageDict) and \
			   canSkipCardImageDownload(backImageName, files, existingImageDict):
				continue
			imageNameToCheck = frontImageName
		else:
			imageNameToCheck = safeFilename(cardName) + IMAGE_SUFFIX
			if canSkipCardImageDownload(imageNameToCheck, files, existingImageDict):
				continue

		if USE_FORMAT_SPECIFIC_LANDS and initialCardName in BASIC_LAND_NAMES:
			print("Couldn't find '%s' in the magic images folder or existing images dict.  If you want a format-specific land, you'll have to create it manually.  Using the default %s instead" % (cardName, initialCardName))
			cardName = initialCardName

			imageNameToCheck = safeFilename(cardName) + IMAGE_SUFFIX
			if canSkipCardImageDownload(imageNameToCheck, files, existingImageDict):
				continue

		# try to download from magiccards.info to image directory
		print("%s not downloaded, trying to download from scryfall" % cardName)

		downloadSuccess, needToRerunForThisCard = downloadSingleCardImage(initialCardName, cardName, doubleFacedCardDict, existingImageDict)
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
				createXMLFileForMPCFill(decklistDict, existingImageDict, subDir, files, formatName)
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