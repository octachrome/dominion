This is an attempt to write a genetic algorithm to play the card game Dominion.

The concept is to model a Dominion strategy as a target deck with which you would like to end the game. The computer plays a simple strategy each turn to maximise its buying power with the hand it is dealt, and then spends the money on whatever card most makes its deck closer to the target deck.

The genetic aspect is to start with a number of computer players with different random target decks, play them against each other, and breed the most successful target decks to create the next generation of players. After a few generations, a deck emerges which does reasonably well against a slightly below average human player (that's me.)

The target deck consists of a list of cards, each of which has a preference and a delay. Cards with a higher preference are chosen over cards with a lower preference. If two cards have equal preference, the computer will buy whichever one you have fewer of in your deck. If a card has a delay associated with it, the computer will hold off buying this card for the given number of turns (this is to avoid buying victory cards too early.)

I have only implemented around 15 cards so far (mostly cards from Dominion Intrigue actually.)

To play against the computer with a previously evolved optimal target deck (saved in the source code):

    python dominion.py play

To learn a new target deck:

    python dominion.py learn
