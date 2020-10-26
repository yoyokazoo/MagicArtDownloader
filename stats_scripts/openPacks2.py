# lists average number of packs needed to open before hitting each unique at least once

import random

RARES = 53
MYTHICS = 15
CARDS_ON_SHEET = 121

TRIALS = 100000
total_unique_rares = 0
total_unique_mythics = 0
total_num_packs_rare = 0
total_num_packs_mythic = 0
for t in range(TRIALS):
	rare_cards = {}
	mythic_cards = {}
	found_all_rares = False
	found_all_mythics = False
	num_packs = 0
	while(True):
		num_packs = num_packs + 1
		rarity = random.randint(0,CARDS_ON_SHEET-1)
		if rarity < MYTHICS:
			card = random.randint(0,MYTHICS-1)
			mythic_cards[card] = 1
		else:
			card = random.randint(0,RARES-1)
			rare_cards[card] = 1
		if(not found_all_rares and len(rare_cards) == RARES):
			total_num_packs_rare += num_packs
			found_all_rares = True
		if(not found_all_mythics and len(mythic_cards) == MYTHICS):
			total_num_packs_mythic += num_packs
			found_all_mythics = True
		if(found_all_mythics and found_all_rares):
			break

avg_packs_rare = total_num_packs_rare/TRIALS
avg_packs_mythic = total_num_packs_mythic/TRIALS

print("Packs for Rare: " + str(avg_packs_rare))
print("Packs for Mythic: " + str(avg_packs_mythic))
