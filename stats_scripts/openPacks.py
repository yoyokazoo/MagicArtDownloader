# lists average unique rares and mythics after opening N packs

import random

RARES = 53
MYTHICS = 15
CARDS_ON_SHEET = 121

MIN_PACKS = 100
MAX_PACKS = 100
TRIALS = 100000
avg_rares = []
avg_mythics = []

for packs_to_open in range(MIN_PACKS, MAX_PACKS+1):
	total_unique_rares = 0
	total_unique_mythics = 0
	for t in range(TRIALS):
		rare_cards = {}
		mythic_cards = {}
		for pack in range(packs_to_open):
			rarity = random.randint(0,CARDS_ON_SHEET-1)
			if rarity < MYTHICS:
				card = random.randint(0,MYTHICS-1)
				mythic_cards[card] = 1
			else:
				card = random.randint(0,RARES-1)
				rare_cards[card] = 1
		total_unique_rares += len(rare_cards)
		total_unique_mythics += len(mythic_cards)

	avg_rares.append(total_unique_rares/TRIALS)
	avg_mythics.append(total_unique_mythics/TRIALS)

# for easy google sheets pastability
print("\n\nRARES\n\n")
for avg in avg_rares:
	print(avg)

print("\n\nMYTHICS\n\n")
for avg in avg_mythics:
	print(avg)
