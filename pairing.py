import json
import discord
import random
from collections import defaultdict
from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import List, Dict, Optional, TYPE_CHECKING
import copy
from util import AddSaveLoad


@dataclass_json
@dataclass
class History(AddSaveLoad):
    filename = "history.json"
    channame = "1on1-history"

    # this is mapping from user to list of users they were paired with, can include repeat pairings
    # TODO in the future keep track of if they actually met and then don't add users who were paired but didn't meet to history
    histories: Dict[int, List[int]]

    @classmethod
    def find_possible_pairs(cls, h, used):
        """Generate pairs that are least frequent based on history, excluding already used people."""
        min_pairs = []
        min_count = float("inf")

        # TODO maybe make < O(n^2)? but this is probably fast enough
        for person_i in h:
            if person_i in used:
                continue
            for person_j in h:
                if person_j in used:
                    continue
                if person_i == person_j:
                    continue
                pair = (person_i, person_j)
                count_elem = lambda l, e: sum(1 for x in l if x == e)
                occurrences = count_elem(h[person_i], person_j)
                assert occurrences == count_elem(h[person_j], person_i) # meetings should be symmetric
                if occurrences < min_count:
                    min_pairs = [pair]
                    min_count = occurrences
                elif occurrences == min_count:
                    min_pairs.append(pair)

        return min_pairs

    def update_history(self, pair):
        """Update the history with the new pair."""
        person1, person2 = pair
        self.histories[person1].append(person2)
        self.histories[person2].append(person1)

    def pair_people(self, opt_in=None, filler=None):
        """Pair people by updating history and selecting least frequent pairs. Use opt_in if we only wanted to pair a subset of people."""
        # make a deep copy and then filter to only used opted in people
        if opt_in:
            for p in opt_in:
                if p not in self.histories:
                    self.histories[p] = []
        h = copy.deepcopy(self.histories)
        if opt_in:
            h = {p:self.histories[p] for p in self.histories if p in opt_in}
        pairs = []
        unpaired = []
        # if we have an odd number and a filler id, take a random person and match with filler (making sure that the random person is not a filler)
        if len(h) % 2 == 1:
            person = random.choice(list(h.keys()))
            if not filler:
                unpaired.append(person)
                del h[person]
            else:
                while person == filler:
                    person = random.choice(list(h.keys()))
                pairs.append((person, filler))
                self.update_history((person, filler))
                del h[person]
            
        used = set()

        while len(used) < len(h):
            possible_pairs = History.find_possible_pairs(h, used)
            if possible_pairs:
                pair = random.choice(possible_pairs)
                pairs.append(pair)
                self.update_history(pair)
                used.update(pair)
            else:
                # append the rest of the people to unpaired
                unpaired.extend(set(h.keys()) - used)

        # update self.histories with h
        for person in h:
            self.histories[person] = h[person]

        return pairs, unpaired
    def pair_person(self, person: int, unused: List[List[int]]):
        """Pair a person with the least frequent person in the subarrays of unused. Start with unused[0], but if there are no people in that, go to the rest of unused.
        unused[0] is the people who were left unpaired. unused[1] is the people who can always be paired."""
        for group in unused:
            try: group.remove(person)
            except: pass
            if len(group) == 0: continue
            group.shuffle()
            group.sort(key=lambda x: sum(1 for y in self.histories[x] if y == person))
            p = group[0]
            self.update_history((person, p))
            return p
    @classmethod
    async def load_or_create_new(cls, guild):
        hist = await cls.load(guild)
        if not hist:
            print(f"No history found for guild {guild}, making new history")
            hist = cls(histories={})
        return hist
