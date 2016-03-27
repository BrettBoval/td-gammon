from __future__ import division

import time
import random
import numpy as np
import tensorflow as tf

from backgammon.game import Game
from backgammon.agents.random_agent import RandomAgent
from backgammon.agents.td_gammon_agent import TDAgent

def play(players):
    game = Game.new()
    game.play(players, draw=True)

def test(players, episodes=100, draw=False):
    winners = [0, 0]
    for episode in range(episodes):
        game = Game.new()

        winner = game.play(players, draw=draw)
        winners[winner] += 1

        winners_total = sum(winners)
        print("[Episode %d] %s (%s) vs %s (%s) %d:%d of %d games (%.2f%%)" % (episode, \
            players[0].name, players[0].player, \
            players[1].name, players[1].player, \
            winners[0], winners[1], winners_total, \
            (winners[0] / winners_total) * 100.0))

# TODO: move this to train.py
def train(model, model_path, summary_path, checkpoint_path):
    tf.train.write_graph(model.sess.graph_def, model_path, 'td_gammon.pb', as_text=False)
    summary_writer = tf.train.SummaryWriter('{0}{1}'.format(summary_path, int(time.time()), model.sess.graph_def))

    # the agent plays against itself, making the best move for each player
    players = [TDAgent(Game.TOKENS[0], model), TDAgent(Game.TOKENS[1], model)]
    players_test = [TDAgent(Game.TOKENS[0], model), RandomAgent(Game.TOKENS[1])]

    validation_interval = 2000
    episodes = 20000

    for episode in range(episodes):
        if episode != 0 and episode % validation_interval == 0:
            test(players_test, episodes=100)

        game = Game.new()
        player_num = random.randint(0, 1)

        x = game.extract_features(players[player_num].player)

        game_step = 0
        while not game.is_over():
            game.next_step(players[player_num], player_num)
            player_num = (player_num + 1) % 2

            x_next = game.extract_features(players[player_num].player)
            V_next = model.get_output(x_next)
            model.sess.run(model.train_op, feed_dict={ model.x: x, model.V_next: V_next })

            x = x_next
            game_step += 1

        winner = game.winner()

        _, global_step, summaries, _ = model.sess.run([
            model.train_op,
            model.global_step,
            model.summaries_op,
            model.reset_op
        ], feed_dict={ model.x: x, model.V_next: np.array([[winner]], dtype='float') })
        summary_writer.add_summary(summaries, global_step=global_step)

        print("Game %d/%d (Winner: %s) in %d turns" % (episode, episodes, players[winner].player, game_step))
        model.saver.save(model.sess, checkpoint_path + 'checkpoint', global_step=global_step)

    summary_writer.close()

    test(players_test, episodes=1000)
