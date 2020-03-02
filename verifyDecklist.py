import os
import re
import cards
import argparse

# add arg parsing to pass in a single decklist/folder of decklists
DECKLIST_SUFFIX = ".txt"

DEFAULT_DECKLIST_DIRECTORY_ROOT = ".%sdecklists" % os.path.sep
DEFAULT_JSON_DIRECTORY_ROOT  = ".%s" % os.path.sep

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

MAINDECK_REGEX = "\s*[mM]ain\s*[dD]eck:?\s*"
SIDEBOARD_REGEX = "\s*[sS]ide\s*[bB]oard:?\s*"
REGEX_PATH_SEP = "\\\\" if os.path.sep == "\\" else os.path.sep
FORMAT_NAME_REGEX = "([\w\s\'']*)" + REGEX_PATH_SEP + "([\w\s\'']*)" + REGEX_PATH_SEP + "([\w\s\'']*)" + DECKLIST_SUFFIX + "$"

AUTO_REPLACE_THRESHOLD = 0.925

allCards = None

# taken directly from https://www.datacamp.com/community/tutorials/fuzzy-string-python
import numpy as np
def levenshtein_ratio_and_distance(s, t, ratio_calc = False):
    """ levenshtein_ratio_and_distance:
        Calculates levenshtein distance between two strings.
        If ratio_calc = True, the function computes the
        levenshtein distance ratio of similarity between two strings
        For all i and j, distance[i,j] will contain the Levenshtein
        distance between the first i characters of s and the
        first j characters of t
    """
    # Initialize matrix of zeros
    rows = len(s)+1
    cols = len(t)+1
    distance = np.zeros((rows,cols),dtype = int)

    # Populate matrix of zeros with the indeces of each character of both strings
    for i in range(1, rows):
        for k in range(1,cols):
            distance[i][0] = i
            distance[0][k] = k

    # Iterate over the matrix to compute the cost of deletions,insertions and/or substitutions    
    for col in range(1, cols):
        for row in range(1, rows):
            if s[row-1] == t[col-1]:
                cost = 0 # If the characters are the same in the two strings in a given position [i,j] then the cost is 0
            else:
                # In order to align the results with those of the Python Levenshtein package, if we choose to calculate the ratio
                # the cost of a substitution is 2. If we calculate just distance, then the cost of a substitution is 1.
                if ratio_calc == True:
                    cost = 2
                else:
                    cost = 1
            distance[row][col] = min(distance[row-1][col] + 1,      # Cost of deletions
                                 distance[row][col-1] + 1,          # Cost of insertions
                                 distance[row-1][col-1] + cost)     # Cost of substitutions
    if ratio_calc == True:
        # Computation of the Levenshtein Distance Ratio
        Ratio = ((len(s)+len(t)) - distance[row][col]) / (len(s)+len(t))
        return Ratio
    else:
        # print(distance) # Uncomment if you want to see the matrix showing how the algorithm computes the cost of deletions,
        # insertions and/or substitutions
        # This is the minimum number of edits needed to convert string a to string b
        return "The strings are {} edits away".format(distance[row][col])

def populateDecklistDicts(filePath):
	# load it and cram into dictionary
	maindeckDict = {}
	sideboardDict = {}
	currentDict = maindeckDict

	fileContents = open(filePath, 'r').read()
	for line in fileContents.split("\n"):
		maindeck_line = re.search(MAINDECK_REGEX, line)
		if maindeck_line:
			continue

		in_sideboard_now = re.search(SIDEBOARD_REGEX, line)
		if in_sideboard_now:
			currentDict = sideboardDict
			continue

		matches = re.search("(\d*)x?(\s*)(.*)", line)
		cardCount = 1 if matches.group(1) == '' else int(matches.group(1))
		cardName = matches.group(3)

		if cardName:
			currentDict[cardName] = currentDict.get(cardName, 0) + cardCount

	#addDoubleFacedCardsToDict(decklistDict)
	combinedDict = { combinedKey: maindeckDict.get(combinedKey, 0) + sideboardDict.get(combinedKey, 0) for combinedKey in set(maindeckDict) | set(sideboardDict) }
	return combinedDict, maindeckDict, sideboardDict

def replaceCardNameInDecklist(oldCardName, newCardName, filePath):
	print("Replacing %s with %s in %s" % (oldCardName, newCardName, filePath))
	fileContents = None
	with open(filePath) as f:
		fileContents=f.read().replace(oldCardName, newCardName)

		if not fileContents:
			raise Exception("Couldn't open %s, exiting" % filePath)

	with open(filePath, "w") as f:
		f.write(fileContents)

def verifyAndFixDecklistCardnames(combinedDict, filePath):
	for card in combinedDict.keys():
		#print("Checking card %s" % card)
		if not card in allCards.getAllCardnames():
			if card.lower() in allCards.getAllLowercaseCardnames():
				print("Fixing capitalization on %s to %s" % (card, allCards.getAllLowercaseCardnamesDict()[card.lower()]))
				replaceCardNameInDecklist(card, allCards.getAllLowercaseCardnamesDict()[card.lower()], filePath)
				continue

			print("No matching card could be found for %s (%s), checking similar names..." % (card, filePath))
			distances = {}
			for leveshtein_card in allCards.getAllCardnames():
				leveshtein_distance = levenshtein_ratio_and_distance(card,leveshtein_card,ratio_calc = True)
				distances[leveshtein_card] = leveshtein_distance
				#print("leveshtein_distance between %s and %s is %s" % (leveshtein_distance, card, leveshtein_card))
			count = 0
			replacement_choices = []
			sorted_distances = sorted(distances, key=distances.get, reverse=True)
			if distances[sorted_distances[0]] > AUTO_REPLACE_THRESHOLD:
				print("Found similar cardname %s with a match of %s percent, auto-replacing" % (sorted_distances[0], str(round(distances[sorted_distances[0]]*100, 2))))
				replaceCardNameInDecklist(card, sorted_distances[0], filePath)
				continue
			for key in sorted_distances:
				replacement_choices.append(key)
				count += 1
				if count == 1:
					print("\n-------------------------------------------------------\n")
					print("Couldn't find cardname %s (%s). Here are the closest five cardnames: \n" % (card, filePath))
				print("%s) %s %s" % (count, key, distances[key]))
				if count == 5:
					break
			print()
			print("6) This is a custom card, add it to the dictionary of card names (make sure it's spelled how you want it!)")
			print("7) None of these options are good, I'll fix it manually")
			print("\n-------------------------------------------------------\n")
			choice = int(input("Input the number of the cardname you'd like to replace it with: "))

			if choice >= 1 and choice <= 5:
				replaceCardNameInDecklist(card, replacement_choices[choice-1], filePath)
			elif choice == 6:
				print("Adding %s to custom cards file" % card)
				allCards.addCardToCustomCards(card)
			elif choice == 7:
				print("Skipping %s in %s, probably needs to be fixed in the file manually." % (card, filePath))
			else:
				raise Exception("Invalid choice!")

def verifySingleDecklistForCardnames(filePath):
	combinedDict, maindeckDict, sideboardDict = populateDecklistDicts(filePath)
	verified = verifyAndFixDecklistCardnames(combinedDict, filePath)

def verifyAllDecklistCardnames(args):
	for subDir, dirs, files in os.walk(getDecklistDirectory(args)):
		for fileName in files:
			if fileName == "TestCards.txt":
				continue
			if fileName.endswith(DECKLIST_SUFFIX):
				filePath = os.path.join(subDir, fileName)
				verifySingleDecklistForCardnames(filePath)

	print("Done verifying decklists")

def findAllFilePathsWithSoupPlayerName(args):
	path_to_exclude = "asfdasdfasdf"

	file_paths = []
	for subDir, dirs, files in os.walk(getDecklistDirectory(args)):
		for fileName in files:
			filePath = os.path.join(subDir, fileName)
			if path_to_exclude in filePath:
				continue
			if fileName.endswith(DECKLIST_SUFFIX) and args.soup_player in filePath:
				file_paths.append(filePath)
	return file_paths

def getFormatNameFromFilePath(filePath):
	formatNameMatches = re.search(FORMAT_NAME_REGEX, filePath)
	formatName = formatNameMatches.group(1) if formatNameMatches else ""
	return formatName

def automaticallyAssignSetToCardIfPossible(soup_card, soup_decklist_dict, soup_options_dict, final_decklist):
	differentSetsAvailable = len(set(soup_options_dict[soup_card]))
	#print("%s has %d options available" % (soup_card, differentSetsAvailable))
	if differentSetsAvailable == 1:
		soup_decklist_dict[soup_card] -= 1
		inner_options_array = final_decklist.get(soup_card, [])
		inner_options_array.append(soup_options_dict[soup_card].pop())
		final_decklist[soup_card] = inner_options_array


def verifySoupDecklist(args):
	verifyAllDecklistCardnames(args)
	verifySingleDecklistForCardnames(args.filename)
	soupCombinedDict, soupMaindeckDict, soupSideboardDict = populateDecklistDicts(args.filename)

	print(args.soup_player)
	print(args.filename)
	pantry_filepaths = findAllFilePathsWithSoupPlayerName(args)
	print(len(pantry_filepaths))
	maindeck_decklists = {}
	sideboard_decklists = {}
	for filePath in pantry_filepaths:
		_, maindeck, sideboard = populateDecklistDicts(filePath)
		maindeck_decklists[filePath] = maindeck
		sideboard_decklists[filePath] = sideboard

		print("\n-----------------------------------%s-----------------------------------\n" % filePath)
		print("Maindeck (%d cards): \n%s" % (sum(maindeck.values()), maindeck))
		print()
		print("Sideboard (%d cards): \n%s" % (sum(sideboard.values()), sideboard))


	print("\n\n%s\n%s\n" % (soupMaindeckDict, soupSideboardDict))

	soup_options_dict = {}
	for soup_card, soup_card_count in soupMaindeckDict.items():
		if soup_card in cards.BASIC_LAND_NAMES:
			continue
		#print("%s%s" % (soup_card, soup_card_count))
		for maindeck_decklist_filepath, maindeck_decklist in maindeck_decklists.items():
			if soup_card in maindeck_decklist:
				# dict method
				# inner_options_dict = soup_options_dict.get(soup_card, {})
				# inner_options_dict[getFormatNameFromFilePath(maindeck_decklist_filepath)] = maindeck_decklist[soup_card]
				# soup_options_dict[soup_card] = inner_options_dict
				# array method
				inner_options_array = soup_options_dict.get(soup_card, [])
				for count in range(maindeck_decklist[soup_card]):
					inner_options_array.append(getFormatNameFromFilePath(maindeck_decklist_filepath))
				soup_options_dict[soup_card] = inner_options_array

	#print(soup_options_dict)

	final_decklist = {}
	for soup_card, soup_card_options in soup_options_dict.items():
		print(soup_card, soup_card_options)

	for soup_card, soup_card_count in soupMaindeckDict.items():
		if soup_card in cards.BASIC_LAND_NAMES:
			continue

		for inner_card_count in range(soup_card_count):
			automaticallyAssignSetToCardIfPossible(soup_card, soupMaindeckDict, soup_options_dict, final_decklist)

	print("\n\n%s\n\n%s\n\n%s\n\n" % (final_decklist, soup_options_dict, soupMaindeckDict))

	#print(maindeck_decklists)
	#print(sideboard_decklists)


# Go through all the "well this card HAS to come from this set" options out of the way
# If any options are now illegal -- AKA already used in 5 places in the final decklist, remove them from the remaining options
# Keep repeating the above 2 steps until nothing changes
# Pick a card, and assign a set to it
# Repeat until no more cards to assign

parser = argparse.ArgumentParser()
parser.add_argument('-s', '--soup_player', help="Name of the player's pantry you're raiding")
parser.add_argument('-f', '--filename', help="Filename of the decklist to check")
parser.add_argument('-d', '--decklistDirectory', help="Directory of the source decklists to check")
parser.add_argument('-j', '--jsonDirectory', help="Directory of the source json to check")
args = parser.parse_args()
print(args)

allCards = cards.Cards(getCardJsonDirectory(args))

if args.soup_player and args.filename:
	verifySoupDecklist(args)
else:
	verifyAllDecklistCardnames(args)