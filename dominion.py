#!/usr/bin/python

import sys
import random
import logging
import unittest
import cmd
import itertools

def log(name, msg, *args):
    logging.getLogger(name).info(msg, *args)

class Card:
    def __init__(self, cost, cash=0, victory=0, action=None):
        self.cost = cost
        self.cash = cash
        self.victory = victory
        self.action = action

    def waysToPlayCard(self, hand):
        assert self.action
        return self.action.waysToPlayCard(hand)

#miningVillage = Card('mining-village', action=Choose(3, [
#    GainCards(1),
#    GainActions(2),
#    Optional(TrashThis())
#]))

class Action(object):
    def describe(self):
        raise Error('All actions must implement describe')

    def apply(self, hand):
        raise Error('All actions must implement apply')

    def playHuman(self, hand):
        self.apply(hand)
        return True

    def waysToPlayCard(self, hand):
        self.apply(hand)
        return [hand]

class GainActions(Action):
    def __init__(self, gain):
        self.gain = gain

    def apply(self, hand):
        hand.actions += self.gain
        return [hand]

    def describe(self):
        return '+%s action(s)' % self.gain

class GainCards(Action):
    def __init__(self, gain, replace=0):
        self.gain = gain
        self.replace = replace

    def apply(self, hand):
        if self.canGain(hand):
            hand.deckActions += ['draw'] * self.gain
            hand.deckActions += ['replace'] * self.replace
        return [hand]

    def describe(self):
        desc = '+%s cards(s)' % self.gain
        if self.replace:
            desc += ', replace %s' % self.replace
        return desc

    def canGain(self, hand):
        return True

class GainCardsIfNoActions(GainCards):
    def __init__(self, gain, replace=0):
        GainCards.__init__(self, gain, replace)

    def canGain(self, hand):
        return hand.countActions() == 0

class GainCardsIfNoActionsTest(unittest.TestCase):
    def test_gainIfNoActions(self):
        action = GainCardsIfNoActions(1)
        start = Hand(cards=['silver'])
        hands = action.waysToPlayCard(start)
        self.assertEquals(len(hands), 1)
        self.assertEquals(hands[0].deckActions, ['draw'])

    def test_noGainIfActions(self):
        action = GainCardsIfNoActions(1)
        start = Hand(cards=['pawn'])
        hands = action.waysToPlayCard(start)
        self.assertEquals(len(hands), 1)
        self.assertEquals(hands[0].deckActions, [])

class GainBuys(Action):
    def __init__(self, gain):
        self.gain = gain

    def apply(self, hand):
        hand.buys += self.gain
        return [hand]

    def describe(self):
        return '+%s buy(s)' % self.gain

class GainCash(Action):
    def __init__(self, gain):
        self.gain = gain

    def apply(self, hand):
        hand.cashOffset += self.gain
        return [hand]

    def describe(self):
        return '+$%s' % self.gain

class DiscardForCash(Action):
    def waysToPlayCard(self, hand):
        # No point discarding cards already worth a dollar
        discardChoices = [card for card in hand.hand if CARDS[card].cash < 1]
        discardChoices.sort() # ensure the tuples are ordered, so we can remove duplicates
        tuples = []
        for k in range(len(discardChoices) + 1):
            tuples += itertools.combinations(discardChoices, k)
        tuples = set(tuples) # remove duplicates
        hands = []
        for tup in tuples:
            h = hand.clone()
            for card in tup:
                h.discard(card)
                h.cashOffset += 1
            hands.append(h)
        return hands

    def playHuman(self, hand):
        print 'Enter cards to discard separated by space'
        inp = raw_input('> ')
        try:
            for c in inp.split():
                hand.discard(c)
                hand.cashOffset += 1
            return True
        except ValueError:
            print 'Your hand does not contain those cards'
            return False

    def describe(self):
        return 'Discard any number of cards. +$1 per card discarded.'

class DiscardForCashTest(unittest.TestCase):
    def test_noDiscardableCards(self):
        action = DiscardForCash()
        start = Hand(cards=['silver', 'silver'])
        hands = action.waysToPlayCard(start)
        self.assertEquals(hands, [start])

    def test_oneTypeOfDiscardableCard(self):
        action = DiscardForCash()
        start = Hand(cards=['province', 'province'])
        hands = action.waysToPlayCard(start)
        self.assertEquals(len(hands), 3)

        # discard one province
        self.assertEquals(hands[0].hand, ['province'])
        self.assertEquals(hands[0].discarded, ['province'])
        self.assertEquals(hands[0].cashOffset, 1)

        # discard both provinces
        self.assertEquals(hands[1].hand, [])
        self.assertEquals(hands[1].discarded, ['province', 'province'])
        self.assertEquals(hands[1].cashOffset, 2)

        # discard nothing
        self.assertEquals(hands[2].hand, ['province', 'province'])
        self.assertEquals(hands[2].discarded, [])
        self.assertEquals(hands[2].cashOffset, 0)

    def test_twoTypesOfDiscardableCard(self):
        action = DiscardForCash()
        start = Hand(cards=['province', 'nobles', 'province', 'nobles'])
        hands = action.waysToPlayCard(start)
        self.assertEquals(len(hands), 9)

def choose(choices):
    c = 1
    for choice in choices:
        print '%s) %s' % (c, choice)
        c += 1
    inp = raw_input('> ')
    if len(inp) == 1:
        choice = ord(inp) - ord('1')
        if choice >= 0 and choice < len(choices):
            return choice
    return -1

class Choose(Action):
    def __init__(self, choices, k=1):
        self.choices = choices
        self.k = k

    def waysToPlayCard(self, hand):
        allHands = []
        tuples = itertools.combinations(self.choices, self.k)
        for tup in tuples:
            hands = [hand.clone()]
            for choice in tup:
                nextHands = []
                for h in hands:
                    nextHands += choice.waysToPlayCard(h)
                hands = nextHands
            allHands += hands
        return allHands

    def describe(self):
        desc = 'Choose %s:' % self.k
        for choice in self.choices:
            desc += '\n  ' + choice.describe()
        return desc

    def playHuman(self, hand):
        print 'Choose %s:' % self.k
        for i in range(self.k):
            print 'Choice %s:' % (i + 1)
            choice = choose([c.describe() for c in self.choices])
            if choice < 0:
                print 'Invalid choice'
                return False
            action = self.choices[choice]
            action.playHuman(hand)
        return True

class ChooseTest(unittest.TestCase):
    def test_choose2(self):
        action = Choose(k=2, choices=[GainCards(1), GainActions(1), GainBuys(1), GainCash(1)])
        start = Hand(Deck())
        hands = action.waysToPlayCard(start)

        self.assertEquals(len(hands), 6)

        # +1 card, +1 action
        self.assertEquals(hands[0].deckActions, ['draw'])
        self.assertEquals(hands[0].actions, 2)
        self.assertEquals(hands[0].buys, 1)
        self.assertEquals(hands[0].cashOffset, 0)

        # +1 card, +1 buy
        self.assertEquals(hands[1].deckActions, ['draw'])
        self.assertEquals(hands[1].actions, 1)
        self.assertEquals(hands[1].buys, 2)
        self.assertEquals(hands[1].cashOffset, 0)

        # +1 card, +$1
        self.assertEquals(hands[2].deckActions, ['draw'])
        self.assertEquals(hands[2].actions, 1)
        self.assertEquals(hands[2].buys, 1)
        self.assertEquals(hands[2].cashOffset, 1)

        # +1 action, +1 buy
        self.assertEquals(hands[3].deckActions, [])
        self.assertEquals(hands[3].actions, 2)
        self.assertEquals(hands[3].buys, 2)
        self.assertEquals(hands[3].cashOffset, 0)

        # +1 action, +$1
        self.assertEquals(hands[4].deckActions, [])
        self.assertEquals(hands[4].actions, 2)
        self.assertEquals(hands[4].buys, 1)
        self.assertEquals(hands[4].cashOffset, 1)

        # +1 buy, +$1
        self.assertEquals(hands[5].deckActions, [])
        self.assertEquals(hands[5].actions, 1)
        self.assertEquals(hands[5].buys, 2)
        self.assertEquals(hands[5].cashOffset, 1)

COURTYARD_ACTION = GainCards(3, replace=1)
PAWN_ACTION = Choose(k=2, choices=[GainCards(1), GainActions(1), GainBuys(1), GainCash(1)])
SECRET_CHAMBER_ACTION = DiscardForCash() # todo: reaction
GREAT_HALL_ACTION = Choose(k=2, choices=[GainCards(1), GainActions(1)])
SHANTY_TOWN_ACTION = Choose(k=2, choices=[GainCardsIfNoActions(2), GainActions(2)])
STEWARD_ACTION = Choose(k=1, choices=[GainCards(2), GainCash(2)]) # todo: trash
NOBLES_ACTION = Choose([GainCards(3), GainActions(2)])

CARDS = {
    'copper': Card(cost=0, cash=1),
    'silver': Card(cost=3, cash=2),
    'gold': Card(cost=6, cash=3),
    'estate': Card(cost=2, victory=1),
    'duchy': Card(cost=5, victory=3),
    'province': Card(cost=8, victory=6),
    'courtyard': Card(cost=2, action=COURTYARD_ACTION),
    'pawn': Card(cost=2, action=PAWN_ACTION),
    'secret-chamber': Card(cost=2, action=SECRET_CHAMBER_ACTION),
    'great-hall': Card(cost=3, victory=1, action=GREAT_HALL_ACTION),
    # todo: masquerade
    'shanty-town': Card(cost=3, action=SHANTY_TOWN_ACTION),
    'steward': Card(cost=3, action=STEWARD_ACTION),
    # todo: swindler
    'nobles': Card(cost=6, victory=2, action=NOBLES_ACTION),
}

VICTORY_COUNT = 8
ACTION_COUNT = 10

DEFAULT_STACKS = {
    'copper': 60,
    'silver': 40,
    'gold': 30,
    'estate': VICTORY_COUNT,
    'duchy': VICTORY_COUNT,
    'province': VICTORY_COUNT,
    'courtyard': ACTION_COUNT,
    'pawn': ACTION_COUNT,
    'secret-chamber': ACTION_COUNT,
    'great-hall': VICTORY_COUNT,
    'shanty-town': ACTION_COUNT,
    'steward': ACTION_COUNT,
    'nobles': VICTORY_COUNT,
}

class Deck:
    def __init__(self, cards={'copper': 7, 'estate': 3}):
        deck = []
        for card in cards:
            quantity = cards[card]
            for i in range(quantity):
                deck.append(card)
        random.shuffle(deck)
        # cards which are waiting to be dealt
        self.deck = deck
        # cards which have been discarded
        self.discards = []
        # count of each card type, including the deck, discards, and those in play
        # (cards being played in the current hand are not included in deck or discards)
        self.cards = dict(cards)

    def draw(self):
        if not self.deck:
            self.shuffle()
        if not self.deck:
            return None
        return self.deck.pop()

    def deal(self, count):
        hand = []
        for i in range(count):
            card = self.draw()
            if card:
                hand.append(card)
        return hand

    # 'undeal' the given card back onto the top of the deck
    def replace(self, card):
        self.deck.append(card)

    # gain a new card, onto the discard pile
    def gain(self, card):
        if card in self.cards:
            self.cards[card] += 1
        else:
            self.cards[card] = 1
        self.discards.append(card)

    def discard(self, card):
        self.discards.append(card)

    def shuffle(self):
        self.deck = self.deck + self.discards
        self.discards = []
        random.shuffle(self.deck)

    def count(self, card):
        if card in self.cards:
            return self.cards[card]
        else:
            return 0

    def size(self):
        total = 0
        for card in self.cards:
            total += self.cards[card]
        return total

    def countVictory(self):
        victory = 0
        for card in self.cards:
            victory += CARDS[card].victory * self.cards[card]
        return victory

    def expectedCash(self):
        count = 0
        cash = 0.0
        for c in self.cards:
            count += self.cards[c]
            cash += CARDS[c].cash * self.cards[c]
        if count == 0:
            return 0
        else:
            return cash / count

class DeckTest(unittest.TestCase):
    def test_expectedCash(self):
        deck = Deck({'copper': 3})
        self.assertEqual(deck.expectedCash(), 1)

        deck = Deck({'copper': 2, 'gold': 2})
        self.assertEqual(deck.expectedCash(), 2)

        deck = Deck({'copper': 2, 'gold': 2, 'estate': 4})
        self.assertEqual(deck.expectedCash(), 1)

class Hand:
    def __init__(self, deck=None, sourceHand=None, cards=[]):
        if sourceHand:
            assert deck == None
            self.hand = list(sourceHand.hand)
            self.played = list(sourceHand.played)
            self.actions = sourceHand.actions
            self.buys = sourceHand.buys
            self.cashOffset = sourceHand.cashOffset
            self.deckActions = list(sourceHand.deckActions)
            self.discarded = list(sourceHand.discarded)
        else:
            if deck:
                self.hand = deck.deal(5)
                log('hand', 'Dealt hand: %s', self.hand)
            else:
                # This mode is for testing
                self.hand = cards
            self.played = []
            self.actions = 1;
            self.buys = 1;
            self.cashOffset = 0;
            self.deckActions = []
            self.discarded = []
        self.collateCards()

    def __repr__(self):
        return 'Hand(hand=%r,actions=%r,buys=%r,deckActions=%r,played=%r,cashOffset=%r,discarded=%r)' % \
            (self.hand, self.actions, self.buys, self.deckActions, self.played, self.cashOffset, self.discarded)

    def __eq__(self, other):
        return self.hand == other.hand and self.played == other.played and self.actions == other.actions and \
            self.buys == other.buys and self.cashOffset == other.cashOffset and self.deckActions == other.deckActions and \
            self.discarded == other.discarded

    def clone(self):
        return Hand(sourceHand=self)

    def collateCards(self):
        self.collated = {}
        for card in self.hand:
            if card in self.collated:
                self.collated[card] += 1
            else:
                self.collated[card] = 1

    def countCash(self):
        cash = self.cashOffset
        for card in self.collated:
            cash += self.collated[card] * CARDS[card].cash
        return cash

    def countActions(self):
        actions = 0
        for card in self.collated:
            if CARDS[card].action:
                actions += self.collated[card]
        return actions

    def getActions(self):
        return [card for card in self.collated if CARDS[card].action]

    def count(self, card):
        if card in self.collated:
            return self.collated[card]
        else:
            return 0

    def play(self, card):
        self.hand.remove(card)
        self.collated[card] -= 1
        self.played.append(card)

    def discard(self, card):
        self.hand.remove(card)
        self.collated[card] -= 1
        self.discarded.append(card)

    def discardHand(self):
        cards = list(self.hand)
        for card in cards:
            self.discard(card)

    def draw(self, deck, count):
        cards = deck.deal(count)
        log('hand', 'Drew: %s', cards)
        self.hand += cards
        self.collateCards()

    def finish(self, deck):
        self.discardHand()
        for card in self.discarded + self.played:
            deck.discard(card)
        self.discarded = []
        self.played = []
        self.actions = 0;
        self.buys = 0;
        self.cashOffset = 0;
        self.deckActions = []

    def choices(self):
        return [card for card in self.collated if self.collated[card] > 0]

    def waysToPlayHand(self):
        if self.actions == 0 or self.countActions() == 0:
            return [self]
        # we have an action to use, and a card to play it with
        results = []
        for c in self.collated:
            if self.collated[c] == 0:
                continue
            card = CARDS[c]
            if card.action:
                hand = self.clone()
                hand.play(c)
                hand.actions -= 1
                # list of possible hands resulting from playing the card in different ways
                possibleHands = card.waysToPlayCard(hand)
                # now play more hands
                for possibleHand in possibleHands:
                    # continue to play more actions if there are any
                    results += possibleHand.waysToPlayHand()

        # there is always the option to do nothing
        results.append(self)
        return results

    def gainedCards(self):
        return self.deckActions.count('draw') - self.deckActions.count('replace');

    def expectedCash(self, deck):
        # could be smarter by replacing victory-only cards and counting cash value of all drawn cards
        return self.countCash() + self.gainedCards() * deck.expectedCash()

    def performDeckActions(self, deck, cardToReplace):
        for card in self.discarded:
            deck.discard(card)
        self.discarded = []
        for action in self.deckActions:
            if action == 'draw':
                self.draw(deck, 1)
            elif action == 'replace':
                card = cardToReplace(self)
                self.hand.remove(card)
                self.collateCards()
                deck.replace(card)
        self.deckActions = []

class HandTest(unittest.TestCase):
    def test_bestHand(self):
        deck = Deck({'copper': 3, 'nobles': 2})
        hand = Hand(deck)
        hands = hand.waysToPlayHand()
        best = bestHand(hands, deck)
        self.assertEqual(best.played, ['nobles'] * 2)
        self.assertEqual(best.actions, 1)
        self.assertEqual(best.gainedCards(), 3)

class Table:
    def __init__(self, stacks = DEFAULT_STACKS):
        self.stacks = dict(stacks)

    def isGameEnd(self):
        if not 'province' in self.stacks or self.stacks['province'] == 0: return True
        depleted = 0
        for card in self.stacks:
            if self.stacks[card] == 0:
                depleted += 1
                if depleted == 2:
                    return True
        return False

    def count(self, card):
        if not card in self.stacks:
            return 0
        else:
            return self.stacks[card]

    def buy(self, card, deck):
        assert self.count(card) > 0
        self.stacks[card] -= 1
        deck.gain(card)

    def availableCards(self):
        return [k for k in self.stacks if self.stacks[k] > 0]

def bestHand(hands, deck):
    best = None
    for hand in hands:
        if not best:
            best = hand
        elif hand.expectedCash(deck) > best.expectedCash(deck):
            best = hand
        elif hand.expectedCash(deck) == best.expectedCash(deck) and hand.actions > best.actions:
            best = hand
    return best

class Player:
    def __init__(self, table, cardPrefs):
        self.table = table
        self.deck = Deck()
        self.cardPrefs = cardPrefs
        self.delays = {}
        for card in cardPrefs:
            self.delays[card] = cardPrefs[card][1]

    def playHand(self, buy=True):
        hand = Hand(self.deck)
        hand = self.playActions(hand)
        cash = hand.countCash()
        if buy:
            self.playBuys(hand)
        hand.finish(self.deck)
        return cash

    def playActions(self, hand):
        # this is too eager - it plays several actions without determining the outcome (cards drawn) after the first
        while hand.actions > 0 and hand.countActions() > 0:
            results = hand.waysToPlayHand()
            best = bestHand(results, self.deck)
            if best == hand:
                log('play', 'No further actions')
                return hand
            else:
                log('play', 'Played hand: %r' % hand)
                hand.performDeckActions(self.deck, self.cardToReplace)
                hand = best
        return hand

    def cardToReplace(self, hand):
        # simple strategy - optimise the current turn
        # if we have no remaining actions, put an action on the deck for next turn
        if hand.actions == 0:
            for c in hand.hand:
                if CARDS[c].action:
                    return c
        # otherwise put a plain victory card back
        for c in hand.hand:
            card = CARDS[c]
            if card.victory and not card.action and not card.cash:
                return c
        # otherwise put the lowest cash value card back
        lowest = None
        lowestCash = 1000
        for c in hand.hand:
            card = CARDS[c]
            if card.cash < lowestCash:
                lowest = c
                lowestCash = card.cash
        return lowest

    def playBuys(self, hand):
        cash = hand.countCash()
        if cash == 0: return
        log('buy', 'Cash: %s' % cash)
        bestCards = []
        for c in self.cardPrefs:
            card = CARDS[c]
            if card.cost > cash: continue
            if self.table.count(c) == 0: continue
            if self.delays[c] > 0:
                self.delays[c] -= 1
                continue

            if not bestCards or self.compareCards(c, bestCards[0]) > 0:
                bestCards = [c]
            elif self.compareCards(bestCards[0], c) == 0:
                # several cards are equally good, choose randomly
                bestCards.append(c)

        if bestCards:
            c = random.choice(bestCards)
            log('buy', 'Buying %s', c)
            self.table.buy(c, self.deck)
            hand.buys -= 1
        else:
            log('buy', 'No buy')

    def compareCards(self, card1, card2):
        pref1 = self.pref(card1)
        pref2 = self.pref(card2)
        if pref1 != pref2:
            return pref1 - pref2
        else:
            # cards are equally preferred, choose the one we have fewer of (note sign reversal)
            return self.deck.count(card2) - self.deck.count(card1)

    def pref(self, card):
        return self.cardPrefs[card][0] if card in self.cardPrefs else 0

    def averageSpendTest(self, hands=20):
        results = {}
        total = 0
        bigCashHands = 0
        for i in range(hands):
            cash = self.playHand(False)
            if cash in results:
                results[cash] += 1
            else:
                results[cash] = 1
            total += cash
            if cash > 8:
                bigCashHands += 1
        print 'Average cash per hand over', hands, 'hands:', (total / hands)
        print 'Hands with >$8', bigCashHands
        print results

class HumanPlayer(Player):
    def __init__(self, table):
        self.table = table
        self.deck = Deck()
        self.hand = None

    def startHand(self):
        self.hand = Hand(self.deck)

    def buy(self, cardName):
        if not cardName in CARDS:
            print 'No such card'
            return False

        card = CARDS[cardName]
        cash = self.hand.countCash()
        if cash < card.cost:
            print 'Too expensive'
            return False

        if self.table.count(cardName) == 0:
            print 'None left'
            return False

        print 'Buying', cardName
        self.table.buy(cardName, self.deck)
        self.hand.buys -= 1
        self.hand.cashOffset -= card.cost
        return True

    def play(self, cardName):
        if self.hand.actions == 0:
            print 'No more actions'
        elif not cardName in self.hand.getActions():
            print 'Cannot play this card'
        else:
            card = CARDS[cardName]
            if card.action:
                hand = self.hand.clone()
                hand.play(cardName)
                hand.actions -= 1
                if card.action.playHuman(hand):
                    hand.performDeckActions(self.deck, self.cardToReplace)
                    self.hand = hand
                else:
                    print 'Action not played'
            else:
                print 'No action'

    def cardToReplace(self, hand):
        cards = hand.choices()
        while True:
            print 'Choose a card to replace on the deck:'
            choice = choose(cards)
            if choice >= 0:
                return cards[choice]

    def finishHand(self):
        if self.hand:
            self.hand.finish(self.deck)
            self.hand = None

MAX_HANDS = 100

def playGame(chromes, firstPlayer=0):
    table = Table()
    players = []
    for chrome in chromes:
        players.append(Player(table, chrome))

    hands = 0
    while not table.isGameEnd() and hands < MAX_HANDS:
        p = (hands + firstPlayer) % len(players)
        players[p].playHand()
        hands += 1

    if not table.isGameEnd():
        log('game', 'Game timed out after %s hands', hands)

    score0 = players[0].deck.countVictory()
    score1 = players[1].deck.countVictory()
    if score0 == score1:
        log('game', 'Draw after %s hands', hands)
        return -1
    elif score0 > score1:
        log('game', 'Player 0 won after %s hands', hands)
        return 0
    else:
        log('game', 'Player 1 won after %s hands', hands)
        return 1

def bestOf(chromes, games=500):
    wins = [0, 0]
    for i in range(games):
        result = playGame(chromes, i % 2)
        if result >= 0:
            wins[result] += 1
    print wins

def randomChrome():
    chrome = {}
    for c in CARDS:
        if c == 'copper':
            chrome[c] = (0,0)
        else:
            chrome[c] = (random.randint(0, 5),0)
    return chrome

def randomPopulation(size=20):
    chromes = []
    for i in range(size):
        chromes.append(randomChrome())
    return chromes

def fightAll(chromes):
    wins = [0] * len(chromes)
    # best of 5, both ways
    for i in range(5):
        for p1 in range(len(chromes)):
            for p2 in range(len(chromes)):
                if p1 == p2:
                    continue
                c1 = chromes[p1]
                c2 = chromes[p2]
                result = playGame([c1, c2])
                if result == 0:
                    wins[p1] += 1
                elif result == 1:
                    wins[p2] += 1
    return wins

def breed(parent1, parent2):
    child = {}
    for card in CARDS:
        if card in parent1 and card in parent2:
            child[card] = random.choice([parent1[card], parent2[card]])
        elif card in parent1:
            child[card] = parent1[card]
        elif card in parent2:
            child[card] = parent2[card]
    return child

def nextGeneration(chromes, wins):
    sampleSpace = []
    nextGen = []
    for i in range(len(chromes)):
        chrome = chromes[i]
        sampleSpace += [chrome] * wins[i]
    for i in range(len(chromes)):
        c1 = c2 = random.choice(sampleSpace)
        while c1 is c2:
            c2 = random.choice(sampleSpace)
        child = breed(c1, c2)
        nextGen.append(child)
    return nextGen

def mutateGeneration(chromes, rate):
    n = int(rate * len(chromes) * len(CARDS))
    for i in range(n):
        # index of chromasome to mutate
        c = random.randrange(len(chromes))
        # which card to mutate
        card = random.choice(CARDS.keys())
        pref = chromes[c][card]
        # which attribute to mutate (preference or delay)
        attr = random.randrange(2)
        # how much to mutate by
        delta = random.choice([-1, 1])
        newAttr = pref[attr] + delta
        if delta < 0: continue
        if attr == 0:
            newPref = (newAttr, pref[1])
        else:
            newPref = (pref[0], newAttr)

        chromes[c][card] = newPref

def fittest(chromes, wins):
    bestScore = wins[0]
    fittest = chromes[0]
    for i in range(len(chromes)):
        if wins[i] > bestScore:
            bestScore = wins[i]
            fittest = chromes[i]
    return fittest

class GameCmd(cmd.Cmd):
    def start(self, chrome):
        self.table = Table()
        self.human = HumanPlayer(self.table)
        self.computer = Player(self.table, chrome)

        if not self.nextTurn():
            self.cmdloop()

    def nextTurn(self):
        self.human.finishHand()
        if self.checkGameEnd():
            return True

        print '\nComputer:'
        self.computer.playHand();
        if self.checkGameEnd():
            return True

        print '\nYou:'
        self.human.startHand();

    def checkGameEnd(self):
        if self.table.isGameEnd():
            hscore = self.human.deck.countVictory()
            cscore = self.computer.deck.countVictory()
            print "Score: you %s, computer %s" % (hscore, cscore)
            if hscore == cscore:
                print 'Draw'
            elif hscore > cscore:
                print 'You win'
            else:
                print 'Computer wins'
            return True
        return False

    def checkTurnEnd(self):
        if self.human.hand.buys == 0:
            print 'Turn ended'
            return self.nextTurn()
        else:
            print 'Hand: %s ($%s total)' % (self.human.hand.hand, self.human.hand.countCash())
            print '%s action(s) and %s buy(s) remaining' % (self.human.hand.actions, self.human.hand.buys)
            return False

    def do_exit(self, arg):
        return True

    def do_quit(self, arg):
        return True

    def do_done(self, arg):
        return self.nextTurn()

    def do_play(self, cardName):
        self.human.play(cardName)
        return self.checkTurnEnd()

    def complete_play(self, text, line, begidx, endidx):
        return self.findWithPrefix(text, set(self.human.hand.getActions()))

    def do_buy(self, card):
        self.human.buy(card)
        return self.checkTurnEnd()

    def complete_buy(self, text, line, begidx, endidx):
        return self.findWithPrefix(text, self.table.availableCards())

    def do_describe(self, cardName):
        if not cardName in CARDS:
            print 'Unknown card'
        else:
            card = CARDS[cardName]
            if card.cost:
                print 'Cost: $%s' % card.cost
            if card.victory:
                print 'Victory points: %s' % card.victory
            if card.cash:
                print 'Cash value: $%s' % card.cash
            if card.action:
                print card.action.describe()

    def findWithPrefix(self, prefix, options):
        return [o for o in options if o.startswith(prefix)]

logging.basicConfig(format="%(message)s", level=logging.INFO)

FITTEST_SO_FAR = {'province': (10, 1), 'copper': (2, 1), 'estate': (0, 0), 'pawn': (0, 0), 'shanty-town': (3, 1),
    'great-hall': (3, 0), 'duchy': (4, 0), 'steward': (4, 0), 'courtyard': (1, 3), 'secret-chamber': (3, 2),
    'nobles': (4, 0), 'gold': (6, 0), 'silver': (5, 0)}

# simple baseline strategy
GOLD_N_NOBLES = {
    'silver': (1,0),
    'gold': (2,0),
    'nobles': (2,0),
    'province': (3,3)
}

def learn():
    # random.seed(1)

    logging.getLogger('hand').setLevel(logging.WARNING)
    logging.getLogger('action').setLevel(logging.WARNING)
    logging.getLogger('cash').setLevel(logging.WARNING)
    logging.getLogger('buy').setLevel(logging.WARNING)
    logging.getLogger('game').setLevel(logging.WARNING)
    logging.getLogger('play').setLevel(logging.WARNING)

    chromes = randomPopulation(10)
    chromes[0] = FITTEST_SO_FAR

    for i in range(20):
        wins = fightAll(chromes)
        f = fittest(chromes, wins)
        print 'Fittest: %s' % f
        chromes = nextGeneration(chromes, wins)
        mutateGeneration(chromes, 0.2)
        # keep the fittest without breeding or mutation
        chromes[0] = f

    print 'New fittest vs. previous:'
    bestOf([chromes[0], FITTEST_SO_FAR])

    print 'New fittest vs. simple human strategy:'
    bestOf([chromes[0], GOLD_N_NOBLES])

if __name__ == '__main__':
    command = sys.argv[1] if len(sys.argv) > 1 else 'play'
    if command == 'test':
        unittest.main(__name__, None, [sys.argv[0]])
    elif command == 'play':
        GameCmd().start(FITTEST_SO_FAR)
    elif command == 'learn':
        learn()
    else:
        print 'Unknown command %s' % command
        print 'Usage: dominion.py play|learn|test'
