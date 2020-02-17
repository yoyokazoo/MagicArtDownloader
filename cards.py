import os
import json

ALL_CARDS_FILENAME = "AllCards.json"

if not os.path.isfile(ALL_CARDS_FILENAME):
		raise Exception("Couldn't find AllCards.json!  Download it from https://mtgjson.com/downloads/all-files/")

ALL_CARDS = None
if ALL_CARDS is None:
	print("Loading cards.json")
	with open(ALL_CARDS_FILENAME, 'r', encoding="utf-8") as all_cards_file:
		ALL_CARDS = json.load(all_cards_file)
		ALL_CARDNAMES = ALL_CARDS.keys()
	print("Done loading cards.json")