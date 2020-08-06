"""
Agent Class.
"""
from random import sample, seed
from collections import deque
import numpy as np
import torch as T
from network import DeepQNetwork
from params import Params

class Agent():
    """
    Agent Class.
    """
    def __init__(self):
        self.params = Params()

        if self.params.seed:
            seed(self.params.seed)

        self.action_space = [i for i in range(self.params.action_size)]
        self.state_size = (self.params.vision_grid, self.params.vision_grid, self.params.state_features)

        self.experience_replay = deque(maxlen=self.params.memory_size)

        self.batch_counter = 1
        self.align_counter = 1
        self.q_eval = DeepQNetwork()
        self.q_next = DeepQNetwork()

        self.align_target()
        self.random_action = True

    def store(self, state, action, reward, next_state):
        """
        Store rewards and states for experience replay.
        """
        self.experience_replay.append((state, action, reward, next_state))
        if self.batch_counter % self.params.batch_size == 0:
            self.retrain()
        self.batch_counter += 1

        # end of random
        if self.batch_counter >= self.params.training_size:
            if self.random_action:
                print("End of random experiences")
            self.random_action = False

        return self.random_action

    def get_weights(self):
        return self.q_eval.state_dict()

    def inherit_network(self, weights):
        """
        Copies the weights from another network
        """
        self.q_eval.load_checkpoint(weights)
        self.align_target()

    def align_target(self):
        """
        Copies the weights from another network
        """
        self.q_next.load_state_dict(self.q_eval.state_dict())

    def act(self, state):
        """
        Produces a q table
        """
        return self.q_eval.forward(state)

    def sample_memory(self):
        """
        Returns random sample of experience replay.
        """
        batch = sample(self.experience_replay, self.params.batch_size)

        states = np.ndarray((self.params.batch_size, self.params.state_features, self.params.vision_grid, self.params.vision_grid))
        actions = np.ndarray(self.params.batch_size)
        future_states = np.ndarray((self.params.batch_size, self.params.state_features, self.params.vision_grid, self.params.vision_grid))
        rewards = np.ndarray(self.params.batch_size)

        for i in range(self.params.batch_size):
            states[i] = batch[i][0]
            actions[i] = batch[i][1]
            rewards[i] = batch[i][2]
            future_states[i] = batch[i][3]

        states = T.tensor(states).to(self.q_eval.device)
        actions = T.tensor(actions).to(self.q_eval.device)
        future_states = T.tensor(future_states).to(self.q_eval.device)
        rewards = T.tensor(rewards).to(self.q_eval.device)

        return states, actions, future_states, rewards

    def retrain(self):
        """
        Train the neural net from a sample of the experience replay items.
        """
        if self.align_counter % self.params.retrain_delay == 0:
            self.align_target()

        if len(self.experience_replay) >= self.params.batch_size:
            self.q_eval.optimizer.zero_grad()

            states, actions, future_states, rewards = self.sample_memory()
            indices = np.arange(self.params.batch_size)

            q_pred = self.q_eval.forward(states)[indices, actions]
            q_next = self.q_next.forward(future_states).max(dim=1)[0]

            q_target = rewards + self.params.discount * q_next

            loss = self.q_eval.loss(q_target, q_pred).to(self.q_eval.device)
            loss.backward()
            self.q_eval.optimizer.step()

        self.align_counter += 1