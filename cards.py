import os
import json

NORMAL_CARDS_FILENAME = "AllCards.json"
CUSTOM_CARDS_FILENAME = "CustomCards.json"

LAYOUTS_WITH_CUSTOM_NAMES = ["split", "aftermath"]

def prepareCustomCardsJson():
	if not os.path.isfile(CUSTOM_CARDS_FILENAME):
		with open(CUSTOM_CARDS_FILENAME, 'w') as custom_cards_file:
			json.dump({}, custom_cards_file)

def addCardToCustomCards(cardname):
	custom_cards_contents = None
	with open(CUSTOM_CARDS_FILENAME, 'r', encoding="utf-8") as custom_cards_file:
		custom_cards_contents = json.load(custom_cards_file)

	if not custom_cards_contents.get(cardname):
		custom_cards_contents[cardname] = {}

	with open(CUSTOM_CARDS_FILENAME, 'w', encoding="utf-8") as custom_cards_file:
		json.dump(custom_cards_contents, custom_cards_file)

def prepareSplitCards(cards_dict):
	print("Preparing double-faced cards")
	for cardname, card in cards_dict.items():
		if card.get('side', "N/A") == 'a' and card['layout'] in LAYOUTS_WITH_CUSTOM_NAMES:
			split_name = " // ".join(card['names'])
			addCardToCustomCards(split_name)

prepareCustomCardsJson()

if not os.path.isfile(NORMAL_CARDS_FILENAME):
		raise Exception("Couldn't find %s!  Download it from https://mtgjson.com/downloads/all-files/" % NORMAL_CARDS_FILENAME)

with open(NORMAL_CARDS_FILENAME, 'r', encoding="utf-8") as all_cards_file:
	NORMAL_CARDS = json.load(all_cards_file)

prepareSplitCards(NORMAL_CARDS)

print("Loading cards jsons")
with open(CUSTOM_CARDS_FILENAME, 'r', encoding="utf-8") as custom_cards_file:
	CUSTOM_CARDS = json.load(custom_cards_file)

ALL_CARDS = {}
ALL_CARDS.update(CUSTOM_CARDS)
ALL_CARDS.update(NORMAL_CARDS)
ALL_CARDNAMES = ALL_CARDS.keys()
ALL_LOWERCASE_CARDNAMES_DICT = {cardname.lower(): cardname for cardname in ALL_CARDNAMES}
ALL_LOWERCASE_CARDNAMES = ALL_LOWERCASE_CARDNAMES_DICT.keys()

print("Done loading cards json")