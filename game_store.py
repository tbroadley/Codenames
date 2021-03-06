from config import global_config as config
from game import CodenameGame
from game_code import *
from game_manager import GameManager
import logging
from player import PlayerRole
import time, threading
from utils import JSONUtils


class ActiveGameStore:
	''' In-memory store for games currently in play (active). '''

	def __init__(self):
		# Mapping of active game codes to game managers.
		self.active_games = {} # Dict[GameCode, GameManager]

	def create_game(self, game_code_option = None):
		''' Wrapper method for creating new game, and adding to game_store.
			If no game code is provided, a new game code is generated (and used).
		'''
		game_code = self.create_game_code() if game_code_option is None else game_code_option
		self.update_game(game_code, GameManager(game_code))

        # Initiate a timer to kill off this game if doesn't have any clients
        # after config.CLEAN_UP_DELTA seconds
		# TODO: this is pretty hacky and bad because it will destroy a game
		# 	    no matter how active it has been, if it has no clients after
		#       CLEAN_UP_DELTA seconds.
		if not __debug__:
			threading.Timer(config.CLEAN_UP_DELTA, lambda: self.watch(game_code)).start()
		return game_code

	def create_game_code(self):
		''' Wrapper method for generating new game code
			with the globally configured game code length.
		'''
		code_len = config.getGameCodeLen()
		return generate_unique_game_code(code_len, self.active_games)

	def remove_game(self, game_code):
		if game_code not in self.active_games:
			raise ValueError("%s not found in game store" % str(game_code))
		del self.active_games[game_code]

	def contains_game(self, game_code):
		''' Checks if active game store contains given game code. '''
		return game_code in self.active_games

	def update_game(self, game_code, new_game):
		''' Overrides stored game at given game code with new provided game. '''
		self.active_games[game_code] = new_game

	def get_game(self, game_code):
		''' Returns specified game by game code.'''
		if game_code not in self.active_games:
			raise ValueError("%s not found in game store" % str(game_code))
		return self.active_games[game_code]

	def watch(self, game_code):
		''' Meant to be called every config.CLEAN_UP_DELTA seconds to check if
			a game has no clients and delete it if that is the case.
	    '''
		logging.info('[CLEAN UP] Checking game %s for clients', str(game_code))
		game_manager = self.get_game(game_code)
		if game_manager.get_num_clients() == 0:
			logging.info('[CLEAN UP] KILLING game %s', str(game_code))
			self.remove_game(game_code)
		else:
			threading.Timer(config.CLEAN_UP_DELTA, lambda: self.watch(game_code)).start()

	def get_game_bundle(self, game_code):
		'''	Returns JSON bundle of all dynamic game information
			that changes incrementally on each turn (for the specified game).
			This includes:
				- GameManager
					- Game code
					- Codename game
						- Deck
						- Red count
						- Blue count
						- Current turn
						- Current clue
						- Activity log
		'''
		return self.get_game(game_code).serialize_game()

	def get_full_game_bundle(self, game_code, role):
		'''	Returns JSON bundle of all game information (for the specified game).
			This includes:
				- GameManager
					- Game code
					- List of serialized playerid to player mapping
					- Board size
					- Map card (iff (if-only-if) SPYMASTER)
					- Codename game
						- Deck
						- Red count
						- Blue count
						- Current turn
						- Current clue
						- Activity log
		'''
		game_manager = self.get_game(game_code)
		game_bundle = game_manager.serialize_game()
		JSONUtils.merge_in_place(game_bundle, game_manager.serialize_players_mapping())
		JSONUtils.include_in_place(game_bundle, 'boardSize', str(config.getNumCards()))
		if role is PlayerRole.SPYMASTER:
			JSONUtils.include_in_place(game_bundle, 'map', game_manager.game.map_card.serialize())
		return game_bundle

	def get_all_active_games(self):
		''' Returns in-memory list of all active game codes. '''
		return [game_code.serialize() for game_code in self.active_games.keys()]

game_store = ActiveGameStore()

# TODO: if debug:

test_game = CodenameGame()
game_store.create_game(GameCode('test'))
#game_store.active_games[GameCode('test')] = test_game
