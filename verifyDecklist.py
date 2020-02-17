import os
import re
import cards

# add arg parsing to pass in a single decklist/folder of decklists
DECKLIST_SUFFIX = ".txt"
DECKLIST_DIR = "decklists/2019/BOOStandard/Kyle"
DECKLIST_TO_CHECK = "_decklist.txt"
DECKLIST_DIRECTORY_ROOT = "./decklists"

MAINDECK_REGEX = "\s*[mM]ain\s*[dD]eck:?\s*"
SIDEBOARD_REGEX = "\s*[sS]ide\s*[bB]oard:?\s*"

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

def populateDecklistDicts(subDir, fileName):
	# load it and cram into dictionary
	maindeckDict = {}
	sideboardDict = {}
	currentDict = maindeckDict

	fileContents = open(os.path.join(subDir, fileName), 'r').read()
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

def verifyDecklist(maindeckDict, sideboardDict):
	print("Verifying decklist %s %s" % (maindeckDict, sideboardDict))
	for card in maindeckDict.keys():
		print("Checking card %s" % card)
		if not card in cards.ALL_CARDNAMES:
			distances = {}
			for leveshtein_card in cards.ALL_CARDNAMES:
				leveshtein_distance = levenshtein_ratio_and_distance(card,leveshtein_card,ratio_calc = True)
				distances[leveshtein_card] = leveshtein_distance
				#print("leveshtein_distance between %s and %s is %s" % (leveshtein_distance, card, leveshtein_card))
			count = 0
			for key in sorted(distances, key=distances.get, reverse=True):
				print(key, distances[key])
				count += 1
				if count == 5:
					break
			print("Couldn't find cardname %s" % card)
			raise Exception()

def verifyAllDecklists():
	for subDir, dirs, files in os.walk(DECKLIST_DIRECTORY_ROOT):
		for fileName in files:
			if fileName.endswith(DECKLIST_SUFFIX):
				combinedDict, maindeckDict, sideboardDict = populateDecklistDicts(subDir, fileName)
				verified = verifyDecklist(maindeckDict, sideboardDict)

verifyAllDecklists()