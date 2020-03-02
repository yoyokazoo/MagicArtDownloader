import os
import json

BASIC_LAND_NAMES = ["Forest", "Island", "Mountain", "Plains", "Swamp"]

class Cards:
	NORMAL_CARDS_FILENAME = "AllCards.json"
	CUSTOM_CARDS_FILENAME = "CustomCards.json"

	LAYOUTS_WITH_CUSTOM_NAMES = ["split", "aftermath"]

	def prepareCustomCardsJson(self):
		if not os.path.isfile(self.customCardsFilePath):
			with open(self.customCardsFilePath, 'w') as custom_cards_file:
				json.dump({}, custom_cards_file)

	def addCardToCustomCards(self, cardname, repopulateCardData=True):
		custom_cards_contents = None
		with open(self.customCardsFilePath, 'r', encoding="utf-8") as custom_cards_file:
			custom_cards_contents = json.load(custom_cards_file)

		if not custom_cards_contents.get(cardname):
			custom_cards_contents[cardname] = {}

		with open(self.customCardsFilePath, 'w', encoding="utf-8") as custom_cards_file:
			json.dump(custom_cards_contents, custom_cards_file)

		# a bit heavy-handed to do a full repopulate but whatever
		if repopulateCardData:
			self.populateCardData()

	def prepareSplitCards(self, cards_dict):
		print("Preparing double-faced cards")
		for cardname, card in cards_dict.items():
			if card.get('side', "N/A") == 'a' and card['layout'] in self.LAYOUTS_WITH_CUSTOM_NAMES:
				split_name = " // ".join(card['names'])
				self.addCardToCustomCards(split_name, repopulateCardData=False)

	def populateCardData(self):
		self.prepareCustomCardsJson()

		if not os.path.isfile(self.normalCardsFilePath):
				raise Exception("Couldn't find %s!  Download it from https://mtgjson.com/downloads/all-files/, or specify a directory for it" % normalCardsFilePath)

		self.normal_cards = None
		with open(self.normalCardsFilePath, 'r', encoding="utf-8") as all_cards_file:
			self.normal_cards = json.load(all_cards_file)

		self.prepareSplitCards(self.normal_cards)

		self.custom_cards = None
		with open(self.customCardsFilePath, 'r', encoding="utf-8") as custom_cards_file:
			self.custom_cards = json.load(custom_cards_file)

		self.all_cards = {}
		self.all_cards.update(self.normal_cards)
		self.all_cards.update(self.custom_cards)
		self.all_cardnames = self.all_cards.keys()
		self.all_lowercase_cardnames_dict = {cardname.lower(): cardname for cardname in self.all_cardnames}
		self.all_lowercase_cardnames = self.all_lowercase_cardnames_dict.keys()

	def getAllCards(self):
		return self.all_cards
	def getAllCardnames(self):
		return self.all_cardnames
	def getAllLowercaseCardnamesDict(self):
		return self.all_lowercase_cardnames_dict
	def getAllLowercaseCardnames(self):
		return self.all_lowercase_cardnames

	def __init__(self, jsonDirectory):
		self.normalCardsFilePath = os.path.join(jsonDirectory, Cards.NORMAL_CARDS_FILENAME)
		self.customCardsFilePath = os.path.join(jsonDirectory, Cards.CUSTOM_CARDS_FILENAME)
		
		self.populateCardData()

		print("Done loading cards json")