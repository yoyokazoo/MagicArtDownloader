import os
import re
import cards
import argparse

# add arg parsing to pass in a single decklist/folder of decklists
DECKLIST_SUFFIX = ".txt"
DECKLIST_DIR = "decklists/2019/BOOStandard/Kyle"
DECKLIST_TO_CHECK = "_decklist.txt"
DECKLIST_DIRECTORY_ROOT = ".%sdecklists" % os.path.sep

MAINDECK_REGEX = "\s*[mM]ain\s*[dD]eck:?\s*"
SIDEBOARD_REGEX = "\s*[sS]ide\s*[bB]oard:?\s*"

AUTO_REPLACE_THRESHOLD = 0.925

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

def verifyAndFixDecklistCardnames(maindeckDict, sideboardDict, filePath):
	#print("Verifying decklist %s %s" % (maindeckDict, sideboardDict))
	for card in maindeckDict.keys():
		#print("Checking card %s" % card)
		if not card in cards.ALL_CARDNAMES:
			if card.lower() in cards.ALL_LOWERCASE_CARDNAMES:
				print("Fixing capitalization on %s to %s" % (card, cards.ALL_LOWERCASE_CARDNAMES_DICT[card.lower()]))
				replaceCardNameInDecklist(card, cards.ALL_LOWERCASE_CARDNAMES_DICT[card.lower()], filePath)
				continue

			print("No matching card could be found for %s, checking similar names..." % card)
			distances = {}
			for leveshtein_card in cards.ALL_CARDNAMES:
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
					print("Couldn't find cardname %s. Here are the closest five cardnames: \n" % card)
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
				cards.addCardToCustomCards(card)
			elif choice == 7:
				print("Skipping %s in %s, probably needs to be fixed in the file manually." % (card, filePath))
			else:
				raise Exception("Invalid choice!")

def verifySingleDecklistForCardnames(filePath):
	combinedDict, maindeckDict, sideboardDict = populateDecklistDicts(filePath)
	verified = verifyAndFixDecklistCardnames(maindeckDict, sideboardDict, filePath)

def verifyAllDecklistCardnames():
	for subDir, dirs, files in os.walk(DECKLIST_DIRECTORY_ROOT):
		for fileName in files:
			if fileName == "TestCards.txt":
				continue
			if fileName.endswith(DECKLIST_SUFFIX):
				filePath = os.path.join(subDir, fileName)
				verifySingleDecklistForCardnames(filePath)

	print("Done verifying decklists")

def findAllFilePathsWithSoupPlayerName(soup_player_name):
	path_to_exclude = "Team Set Sealed"

	file_paths = []
	for subDir, dirs, files in os.walk(DECKLIST_DIRECTORY_ROOT):
		for fileName in files:
			filePath = os.path.join(subDir, fileName)
			if path_to_exclude in filePath:
				continue
			if fileName.endswith(DECKLIST_SUFFIX) and soup_player_name in filePath:
				file_paths.append(filePath)
	return file_paths

def verifySoupDecklist(args):
	verifyAllDecklistCardnames()
	verifySingleDecklistForCardnames(args.filename)
	combinedDict, maindeckDict, sideboardDict = populateDecklistDicts(args.filename)

	print(args.soup_player)
	print(args.filename)
	pantry_filepaths = findAllFilePathsWithSoupPlayerName(args.soup_player)
	print(len(pantry_filepaths))
	maindeck_decklists = []
	sideboard_decklists = []
	for filePath in pantry_filepaths:
		_, maindeck, sideboard = populateDecklistDicts(filePath)
		maindeck_decklists.append(maindeck)
		sideboard_decklists.append(sideboard)

		print("\n-----------------------------------%s-----------------------------------\n" % filePath)
		print("Maindeck (%d cards): \n%s" % (sum(maindeck.values()), maindeck))
		print()
		print("Sideboard (%d cards): \n%s" % (sum(sideboard.values()), sideboard))


	print("\n\n")
	print(maindeckDict)
	print()
	print(sideboardDict)


	#print(maindeck_decklists)
	#print(sideboard_decklists)




parser = argparse.ArgumentParser()
parser.add_argument('-s', '--soup_player', help="Name of the player's pantry you're raiding")
parser.add_argument('-f', '--filename', help="Filename of the decklist to check")
args = parser.parse_args()
print(args)

if args.soup_player and args.filename:
	verifySoupDecklist(args)
else:
	verifyAllDecklistCardnames()