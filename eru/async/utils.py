# coding: utf-8

import random
import string


def random_string(length):
    return ''.join(random.sample(string.digits+string.letters), length)

