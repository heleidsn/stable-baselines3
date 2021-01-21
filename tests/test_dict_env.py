import gym
import numpy as np
import pytest
from gym import spaces

from stable_baselines3 import A2C, DDPG, DQN, PPO, SAC, TD3
from stable_baselines3.common.envs import SimpleMultiObsEnv
from stable_baselines3.common.evaluation import evaluate_policy
from stable_baselines3.common.vec_env import DummyVecEnv, VecFrameStack


class DummyDictEnv(gym.Env):
    """Custom Environment for testing purposes only"""

    metadata = {"render.modes": ["human"]}

    def __init__(self, use_discrete_actions=False, channel_last=False):
        super().__init__()
        if use_discrete_actions:
            self.action_space = spaces.Discrete(3)
        else:
            self.action_space = spaces.Box(low=-1, high=1, shape=(2,), dtype=np.float32)
        N_CHANNELS = 1
        HEIGHT = 64
        WIDTH = 64

        if channel_last:
            obs_shape = (HEIGHT, WIDTH, N_CHANNELS)
        else:
            obs_shape = (N_CHANNELS, HEIGHT, WIDTH)

        self.observation_space = spaces.Dict(
            {
                # Image obs
                "img": spaces.Box(low=0, high=255, shape=obs_shape, dtype=np.uint8),
                # Vector obs
                "vec": spaces.Box(low=-1, high=1, shape=(2,), dtype=np.float32),
                # Discrete obs
                "discrete": spaces.Discrete(4),
            }
        )

    def step(self, action):
        reward = 0.0
        done = False
        return self.observation_space.sample(), reward, done, {}

    def compute_reward(self, achieved_goal, desired_goal, info):
        return np.zeros((len(achieved_goal),))

    def reset(self):
        return self.observation_space.sample()

    def render(self, mode="human"):
        pass


@pytest.mark.parametrize("model_class", [PPO, A2C, DQN, DDPG, SAC, TD3])
def test_dict_spaces(model_class):
    """
    Additional tests for PPO/A2C/SAC/DDPG/TD3/DQN to check observation space support
    with mixed observation.
    """
    use_discrete_actions = model_class not in [SAC, TD3, DDPG]
    # TODO(@J-Travnik): add test for channel last env
    env = DummyDictEnv(use_discrete_actions=use_discrete_actions, channel_last=False)
    env = gym.wrappers.TimeLimit(env, 100)

    kwargs = {}
    n_steps = 256

    if model_class in {A2C, PPO}:
        kwargs = dict(n_steps=128, policy_kwargs=dict(features_extractor_kwargs=dict(features_dim=32)))
    else:
        # Avoid memory error when using replay buffer
        # Reduce the size of the features
        kwargs = dict(
            buffer_size=250,
            policy_kwargs=dict(features_extractor_kwargs=dict(features_dim=32)),
        )
        if model_class == DQN:
            kwargs["learning_starts"] = 0

    model = model_class("MultiInputPolicy", env, gamma=0.5, seed=1, **kwargs)

    model.learn(total_timesteps=n_steps)

    evaluate_policy(model, env, n_eval_episodes=5, warn=False)


@pytest.mark.parametrize("model_class", [PPO, A2C, DQN, DDPG, SAC, TD3])
def test_dict_vec_framestack(model_class):
    """
    Additional tests for PPO/A2C/SAC/DDPG/TD3/DQN to check observation space support
    for Dictionary spaces and VecEnvWrapper using MultiInputPolicy.
    """
    use_discrete_actions = model_class not in [SAC, TD3, DDPG]
    # TODO(@J-Travnik): add test for channel last env
    # TODO(@J-Travnik): add test for more types of dict env (ex: discrete + Box)
    channels_order = {"vec": None, "img": "first"}
    env = DummyVecEnv(
        [lambda: SimpleMultiObsEnv(random_start=True, discrete_actions=use_discrete_actions, channel_last=False)]
    )

    env = VecFrameStack(env, n_stack=3, channels_order=channels_order)

    kwargs = {}
    n_steps = 256

    if model_class in {A2C, PPO}:
        kwargs = dict(n_steps=128, policy_kwargs=dict(features_extractor_kwargs=dict(features_dim=32)))
    else:
        # Avoid memory error when using replay buffer
        # Reduce the size of the features
        kwargs = dict(
            buffer_size=250,
            policy_kwargs=dict(features_extractor_kwargs=dict(features_dim=32)),
        )
        if model_class == DQN:
            kwargs["learning_starts"] = 0

    model = model_class("MultiInputPolicy", env, gamma=0.5, seed=1, **kwargs)

    model.learn(total_timesteps=n_steps)

    evaluate_policy(model, env, n_eval_episodes=5, warn=False)