from unittest import TestCase
from subprocess import check_call, check_output
import os


class TestAnimation(TestCase):

    def test_animation(self):
        print(os.getcwd())
        print(check_output(["animation", "--test_dir", "params/test_data/test-2020-07-22_21-33-20_seed7841"]))
