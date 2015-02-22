#!/usr/bin/python

import random
import logging
import unittest
import cmd

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

class Action:
    def describe(self):
        raise Error('All actions must implement describe')

    def apply(self, hand):
        raise Error('All actions must implement apply')

    def playHuman(self, hand):
        self.apply(hand)
        return True

    def enumActions(self, hand):
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
        hand.deckActions += ['draw'] * self.gain
        hand.deckActions += ['replace'] * self.replace
        return [hand]

    def describe(self):
        desc = '+%s cards(s)' % self.gain
        if self.replace:
            desc += ', replace %s' % self.replace
        return desc

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
    def __init__(self, choices, n=1):
        self.choices = choices
        self.n = n

    def enumActions(self, hand):
        hands = []
        for choice in self.choices:
            h = hand.clone()
            hands += choice.enumActions(h)
        return hands

    def describe(self):
        desc = 'Choose %s:' % self.n
        for choice in self.choices:
            desc += '\n  ' + choice.describe()
        return desc

    def playHuman(self, hand):
        print 'Choose %s:' % self.n
        for i in range(self.n):
            print 'Choice %s:' % (i + 1)
            choice = choose([c.describe() for c in self.choices])
            if choice < 0:
                print 'Invalid choice'
                return False
            action = self.choices[choice]
            action.playHuman(hand)
        return True

NOBLES_ACTION = Choose([GainCards(3), GainActions(2)])
COURTYARD_ACTION = GainCards(3, replace=1)
PAWN_ACTION = Choose(n=2, choices=[GainCards(1), GainActions(1), GainBuys(1), GainCash(1)])

CARDS = {
    'copper': Card(cost=0, cash=1),
    'silver': Card(cost=3, cash=2),
    'gold': Card(cost=6, cash=3),
    'estate': Card(cost=2, victory=1),
    'province': Card(cost=8, victory=6),
    'nobles': Card(cost=6, victory=2, action=NOBLES_ACTION),
    'courtyard': Card(cost=2, action=COURTYARD_ACTION),
    'pawn': Card(cost=2, action=PAWN_ACTION)
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

class Hand:
    def __init__(self, deck=None, sourceHand=None):
        if sourceHand:
            assert deck == None
            self.hand = list(sourceHand.hand)
            self.played = list(sourceHand.played)
            self.actions = sourceHand.actions
            self.buys = sourceHand.buys
            self.cashOffset = sourceHand.cashOffset
            self.deckActions = list(sourceHand.deckActions)
        else:
            assert deck != None
            self.hand = deck.deal(5)
            log('hand', 'Dealt hand: %s', self.hand)
            self.played = []
            self.actions = 1;
            self.buys = 1;
            self.cashOffset = 0;
            self.deckActions = []
        self.collateCards()

    def __repr__(self):
        return 'Hand(hand=%r,actions=%r,buys=%r,deckActions=%r,played=%r)' % (self.hand, self.actions, self.buys, self.deckActions, self.played)

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

    def choices(self):
        return [card for card in self.collated if self.collated[card] > 0]

    def enumActions(self):
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
                possibleHands = card.enumActions(hand)
                # now play more hands
                for possibleHand in possibleHands:
                    # continue to play more actions if there are any
                    results += possibleHand.enumActions()

        # there is always the option to do nothing
        results.append(self)
        return results

    def gainedCards(self):
        return self.deckActions.count('draw') - self.deckActions.count('replace');

    def performDeckActions(self, deck, cardToReplace):
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
        hands = hand.enumActions()
        best = bestHand(hands)

        self.assertEqual(best.played, ['nobles'] * 2)
        self.assertEqual(best.actions, 1)
        self.assertEqual(best.gainedCards(), 3)

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
        deck.gain(card)

def bestHand(hands):
    best = None
    for hand in hands:
        if not best:
            best = hand
        elif hand.gainedCards() > best.gainedCards():
            best = hand
        elif hand.gainedCards() == best.gainedCards() and hand.actions > best.actions:
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
            results = hand.enumActions()
            hand = bestHand(results)
            log('play', 'Played hand: %r' % hand)
            hand.performDeckActions(self.deck, self.cardToReplace)
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
        if not cardName in CARDS:
            print 'Unknown card'
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
    table = Table({'silver': 100, 'gold': 100, 'nobles': 8, 'province': 8, 'courtyard': 10})
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

def randomPopulation(size=20):
    chromes = []
    for i in range(size):
        chrome = {}
        for c in CARDS:
            if c == 'copper':
                chrome[c] = (0,0)
            else:
                chrome[c] = (random.randint(0, 5),0)
        chromes.append(chrome)
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
        child[card] = random.choice([parent1[card], parent2[card]])
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

logging.basicConfig(format="%(message)s", level=logging.INFO)
#logging.getLogger('hand').setLevel(logging.WARNING)
#logging.getLogger('action').setLevel(logging.WARNING)
#logging.getLogger('cash').setLevel(logging.WARNING)
#logging.getLogger('buy').setLevel(logging.WARNING)
#logging.getLogger('game').setLevel(logging.WARNING)
#logging.getLogger('play').setLevel(logging.WARNING)

class GameCmd(cmd.Cmd):
    def start(self, chrome):
        self.table = Table({'silver': 100, 'gold': 100, 'nobles': 8, 'province': 8, 'courtyard': 10, 'pawn': 10})
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

    def do_buy(self, card):
        self.human.buy(card)
        return self.checkTurnEnd()

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

if __name__ == '__main__':
    GameCmd().start({
        'silver': (1,0),
        'gold': (2,0),
        'nobles': (2,0),
        'province': (3,3)
    })

else:
    # unittest.main()

    # random.seed(1)
    chromes = randomPopulation(10)

    for i in range(20):
        wins = fightAll(chromes)
        f = fittest(chromes, wins)
        print 'Fittest: %s' % f
        chromes = nextGeneration(chromes, wins)
        mutateGeneration(chromes, 0.2)
        # keep the fittest without breeding or mutation
        chromes[0] = f

    print 'Fittest vs. simple human strategy:'
    bestOf([
        chromes[0],
        {
            'silver': (1,0),
            'gold': (2,0),
            'nobles': (2,0),
            'province': (3,3)
        }
    ])
