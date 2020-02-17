import os
import json

NORMAL_CARDS_FILENAME = "AllCards.json"
CUSTOM_CARDS_FILENAME = "CustomCards.json"

def prepareCustomCardsJson():
	if not os.path.isfile(CUSTOM_CARDS_FILENAME):
		custom_cards_file = open(CUSTOM_CARDS_FILENAME, 'w')
		custom_cards_file.write("{}")
		custom_cards_file.close()

prepareCustomCardsJson()

if not os.path.isfile(NORMAL_CARDS_FILENAME):
		raise Exception("Couldn't find %s!  Download it from https://mtgjson.com/downloads/all-files/" % NORMAL_CARDS_FILENAME)

print("Loading cards jsons")
with open(CUSTOM_CARDS_FILENAME, 'r', encoding="utf-8") as custom_cards_file:
	CUSTOM_CARDS = json.load(custom_cards_file)

with open(NORMAL_CARDS_FILENAME, 'r', encoding="utf-8") as all_cards_file:
	NORMAL_CARDS = json.load(all_cards_file)

ALL_CARDS = {}
ALL_CARDS.update(CUSTOM_CARDS)
ALL_CARDS.update(NORMAL_CARDS)
ALL_CARDNAMES = ALL_CARDS.keys()
ALL_LOWERCASE_CARDNAMES_DICT = {cardname.lower(): cardname for cardname in ALL_CARDNAMES}
ALL_LOWERCASE_CARDNAMES = ALL_LOWERCASE_CARDNAMES_DICT.keys()

print(ALL_LOWERCASE_CARDNAMES)
print("Done loading cards.json")