import numpy as np
import gym
from gym import spaces
from time import sleep, time
from ..utils.herkulex_socket import HerkulexSocket


class OneLegRealEnv(gym.Env):
    """One leg Hexapod environnement for transfer to real robot."""

    def __init__(self, time_step=0.05, delta=0.5, render=False):
        """
        Init environment.

        Args:
            time_step (float, optional): Environment time step in seconds. Defaults to 0.05.
            delta (float, optional): Size of the random in which the target will be randomly fixed. Defaults to 0.5.
            render (bool, optional): Unused, kept for compatibility.
        """
        super().__init__()

        # 3 actions (servomotors)
        self.n_actions = 3
        self.action_space = spaces.Box(low=-1, high=1,
                                       shape=(self.n_actions,),
                                       dtype="float32")

        # 3*(position,speed) + position target
        self.n_observation = 3*2+3
        self.observation_space = spaces.Box(low=-1, high=1,
                                            shape=(self.n_observation,),
                                            dtype="float32")
        self.observation = np.zeros(self.n_observation, dtype="float32")

        # Environment timestep and constants
        self.dt = time_step
        self.servo_max_speed = 6.308  # rad/s
        self.servo_max_torque = 1.57  # N.m

        # Size of the box in which we pick the target
        self.delta = delta  # from 0 to 1

        # Seed random number generator
        self.seed()

        # Servomotors socket
        self.servomotors = HerkulexSocket(
            max_velocity=self.servo_max_speed,
            max_torque=self.servo_max_torque,
        )

    def reset(self):
        # Reset servomotors
        self.servomotors.reset()
        sleep(1)

        # Set random target and put it in observations
        self.target_position = np.array([
            np.random.uniform(0.219 - 0.069*self.delta,
                              0.219 + 0.069*self.delta),
            np.random.uniform(0.020 - 0.153*self.delta,
                              0.020 + 0.153*self.delta),
            np.random.uniform(0.128 - 0.072*self.delta,
                              0.128 + 0.072*self.delta),
        ])
        self.observation[-3:] = self.target_position

        # Return observation
        self._update_observation()
        return self.observation

    def step(self, action):
        initial_time = time()

        # Update servomotors
        transformed_action = np.array(action) * self.servo_max_speed
        transformed_action *= self.dt  # Training timestep
        self.servomotors.move(list(transformed_action) + [0] * 12)

        # Get observation (slow!)
        self._update_observation()
        while time() - initial_time < self.dt:
            pass # Wait for environment step

        # Return observation, reward and done
        reward = 0  # No reward in real mode
        done = False
        return self.observation, reward, done, {}

    def close(self):
        """Stop servomotors torque."""
        self.servomotors.disableTorque()

    @staticmethod
    def seed(seed=None):
        """Sets the seed for this env's random number generator."""
        np.random.seed(seed)

    def _update_observation(self):
        """
        Update the observation from servomotors sensors.

        Observation contains:
        * 3x servomotor {position, speed}
        * target (x, y, z)
        """
        # Each servomotor position and velocity
        obs, _ = self.servomotors.get_observations()
        self.observation[:2*3] = obs[:2*3]
