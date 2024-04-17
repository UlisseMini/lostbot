import json
import random
from collections import defaultdict


class PairingAlgorithm:
    def __init__(self, people):
        self.people = people
        self.history = self.initialize_history()

    def initialize_history(self):
        """Initialize the history of pairings as a dictionary of sets."""
        history = defaultdict(set)
        for person in self.people:
            history[person] = set()
        return history

    def find_possible_pairs(self, used):
        """Generate pairs that are least frequent based on history, excluding already used people."""
        min_pairs = []
        min_count = float("inf")

        # Check all combinations for the least frequent pairs
        for i in range(len(self.people)):
            if self.people[i] in used:
                continue
            for j in range(i + 1, len(self.people)):
                if self.people[j] in used:
                    continue
                pair = (self.people[i], self.people[j])
                occurrences = len(
                    self.history[self.people[i]].intersection(
                        self.history[self.people[j]]
                    )
                )
                if occurrences < min_count:
                    min_pairs = [pair]
                    min_count = occurrences
                elif occurrences == min_count:
                    min_pairs.append(pair)

        return min_pairs

    def update_history(self, pair):
        """Update the history with the new pair."""
        person1, person2 = pair
        self.history[person1].add(person2)
        self.history[person2].add(person1)

    def pair_people(self, filler=None):
        """Pair people by updating history and selecting least frequent pairs."""
        random.shuffle(self.people)  # Randomize order to ensure variety
        pairs = []
        # if we have an odd number and a filler id, take the last person and match them with the filler
        if len(self.people) % 2 == 1:
            if filler:
                if self.people[-1] == filler:
                    pairs.append((self.people[-2], filler))
                    self.people.remove(self.people[-2])
                else:
                    pairs.append((self.people.pop(), filler))
        used = set()

        while len(used) < len(self.people):
            possible_pairs = self.find_possible_pairs(used)
            if possible_pairs:
                pair = random.choice(possible_pairs)
                pairs.append(pair)
                self.update_history(pair)
                used.update(pair)
            else:
                break

        return pairs

    def serialize_history(self):
        """Serialize the history into JSON format, converting sets to lists."""
        return json.dumps({k: list(v) for k, v in self.history.items()})

    def load_history(self, json_history):
        """Load history from JSON format, converting lists back to sets."""
        self.history = defaultdict(
            set, {k: set(v) for k, v in json.loads(json_history).items()}
        )

