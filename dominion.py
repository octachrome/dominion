#!/usr/bin/python

import random
import logging

def log(name, msg, *args):
    logging.getLogger(name).info(msg, *args)

class Card:
    def __init__(self, cost, cash=0, victory=0, action=None):
        self.cost = cost
        self.cash = cash
        self.victory = victory
        self.action = action

    def enumActions(self, hand):
        assert self.action
        return self.action.enumActions(hand)

#miningVillage = Card('mining-village', action=Choose(3, [
#    GainCards(1),
#    GainActions(2),
#    Optional(TrashThis())
#]))

#nobles = Card('nobles', action=Choose(2, [
#    GainCards(3),
#    GainActions(2)
#]))

class Nobles:
    def enumActions(self, hand):
        h1 = hand.clone()
        h1.actions += 2

        h2 = hand.clone()
        h2.gainedCards += 3

        return [h1, h2]

CARDS = {
    '$1': Card(cost=0, cash=1),
    '$2': Card(cost=3, cash=2),
    '$3': Card(cost=6, cash=3),
    'estate': Card(cost=2, victory=1),
    'province': Card(cost=12, victory=6),
    'nobles': Card(cost=6, victory=2, action=Nobles())
}

class Deck:
    def __init__(self, cards):
        deck = []
        for card in cards:
            quantity = cards[card]
            for i in range(quantity):
                deck.append(card)
        random.shuffle(deck)
        self.deck = deck
        self.discards = []

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

    def discard(self, card):
        self.discards.append(card)

    def shuffle(self):
        self.deck = self.deck + self.discards
        self.discards = []
        random.shuffle(self.deck)

    def allCards(self):
        return self.deck + self.discards

    def count(self, card):
        total = 0
        for c in self.deck:
            if c == card:
                total += 1
        return total

    def countVictory(self):
        victory = 0
        for card in self.allCards():
            victory += CARDS[card].victory
        return victory

class Hand:
    def __init__(self, deck=None, sourceHand=None):
        if sourceHand:
            assert deck == None
            self.hand = list(sourceHand.hand)
            self.played = list(sourceHand.played)
            self.actions = sourceHand.actions
            self.gainedCards = sourceHand.gainedCards
        else:
            assert deck != None
            self.hand = deck.deal(5)
            log('hand', 'Dealt hand: %s', self.hand)
            self.played = []
            self.actions = 1;
            self.gainedCards = 0
        self.collateCards()

    def __repr__(self):
        return 'Hand(hand=%r,actions=%r,gainedCards=%r,played=%r)' % (self.hand, self.actions, self.gainedCards, self.played)

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
        cash = 0
        for card in self.collated:
            cash += self.collated[card] * CARDS[card].cash
        return cash

    def countActions(self):
        actions = 0
        for card in self.collated:
            if CARDS[card].action:
                actions += self.collated[card]
        return actions

    def count(self, card):
        if card in self.collated:
            return self.collated[card]
        else:
            return 0

    def play(self, card):
        self.hand.remove(card)
        self.collated[card] -= 1
        self.played.append(card)

    def discard(self, deck, card):
        self.hand.remove(card)
        self.collated[card] -= 1
        deck.discard(card)

    def discardHand(self, deck):
        cards = list(self.hand)
        for card in cards:
            self.discard(deck, card)

    def discardPlayed(self, deck):
        for card in self.played:
            deck.discard(card)
        self.played = []

    def draw(self, deck, count):
        cards = deck.deal(count)
        log('hand', 'Drew: %s', cards)
        self.hand += cards
        self.collateCards()

    def finish(self, deck):
        self.discardPlayed(deck)
        self.discardHand(deck)

    def enumActions(self):
        if self.actions == 0 or self.countActions() == 0:
            return [self]
        # we have an action to use, and a card to play it with
        results = []
        for c in self.collated:
            card = CARDS[c]
            if card.action:
                hand = self.clone()
                hand.play(c)
                hand.actions -= 1
                # list of possible hands resulting from playing the card in different ways
                possibleHands = card.enumActions(hand)
                # now play more hands
                for possibleHand in possibleHands:
                    # continue to play more actions if there are any
                    results += possibleHand.enumActions()
        return results

        # there is always the option to do nothing
        # results.append(self)

    def drawGainedCards(self, deck):
        if self.gainedCards:
            self.draw(deck, self.gainedCards)
        self.gainedCards = 0

class Table:
    def __init__(self, stacks):
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
        deck.discard(card)

def bestHand(hands):
    best = None
    for hand in hands:
        if not best:
            best = hand
        elif hand.gainedCards > best.gainedCards:
            best = hand
        elif hand.gainedCards == best.gainedCards and hand.actions > best.actions:
            best = hand
    return best

class Player:
    def __init__(self, table, provinceDelay=0):
        self.table = table
        self.deck = Deck({'$1': 5, 'estate': 3})
        self.toggle = 0
        self.provinceDelay = provinceDelay

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
            results = hand.enumActions()
            hand = bestHand(results)
            log('play', 'Played hand: %r' % hand)
            hand.drawGainedCards(self.deck)
        return hand

    def playBuys(self, hand):
        cash = hand.countCash()
        log('cash', 'Total cash: %s', cash)
        if cash >= 8 and self.provinceDelay > 0:
            self.provinceDelay -= 1

        if cash >= 8 and self.provinceDelay == 0:
            if self.buy('province'): return
        elif cash >= 6:
            toggle = self.toggle
            self.toggle = 1 - self.toggle
            if toggle == 1:
                if self.buy('$3'): return
                if self.buy('nobles'): return
            else:
                if self.buy('nobles'): return
                if self.buy('$3'): return
        elif cash >= 3:
            if self.buy('$2'): return
        else:
            log('buy', 'No buy')

    def buy(self, card):
        if self.table.count(card) > 0:
            log('buy', 'Buying %s', card)
            self.table.buy(card, self.deck)
            return True
        else:
            log('buy', 'No more left: %s', card)
            return False

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

MAX_HANDS = 50

def playGame(firstPlayer=0):
    table = Table({'$2': 100, '$3': 100, 'nobles': 12, 'province': 12})
    players = [Player(table, 3), Player(table, 0)]

    hands = 0
    while not table.isGameEnd() and hands < MAX_HANDS:
        p = (hands + firstPlayer) % len(players)
        players[p].playHand()
        hands += 1

    if not table.isGameEnd():
        log('game', 'Game timed out after %s hands', hands)
        return -1
    else:
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

def bestOf(games=500):
    wins = [0, 0]
    for i in range(games):
        result = playGame(i % 2)
        if result >= 0:
            wins[result] += 1
    print wins

logging.basicConfig(format="%(message)s", level=logging.INFO)
logging.getLogger('hand').setLevel(logging.WARNING)
logging.getLogger('action').setLevel(logging.WARNING)
logging.getLogger('cash').setLevel(logging.WARNING)
logging.getLogger('buy').setLevel(logging.WARNING)
logging.getLogger('game').setLevel(logging.WARNING)
logging.getLogger('play').setLevel(logging.WARNING)

if __name__ == '__main__':
    bestOf()
