# calculates chance after opening N packs that you've opened at least one of each unique rare, ignoring mythics

import random

RARES = 53

PACKS_PER_TRIAL = 121
TRIALS = 100000

total_unique_rares = 0
total_unique_mythics = 0
total_successes_rare = 0
total_successes_mythic = 0

for t in range(TRIALS):
	rare_cards = {}
	mythic_cards = {}
	found_all_rares = False
	found_all_mythics = False
	num_packs = 0
	for num_pack in range(1, PACKS_PER_TRIAL+1):
		card = random.randint(0,RARES-1)
		rare_cards[card] = 1
		if(not found_all_rares and len(rare_cards) == RARES):
			total_successes_rare += 1
			found_all_rares = True
			break

avg_successes_rare = total_successes_rare/TRIALS

print("Chances of finding all Rares: " + str(avg_successes_rare))
