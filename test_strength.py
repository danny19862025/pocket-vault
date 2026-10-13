import unittest

from strength import estimate


class StrengthTests(unittest.TestCase):
    def test_common_and_predictable_passwords_stay_weak(self):
        for value in ('password', 'Password123!', 'P@ssw0rd2026!', 'qwerty123',
                      '1234567890', 'abcdefghijklmnop', 'aaaaaaaaaaaaaaaa', 'abcd' * 10):
            with self.subTest(value=value):
                self.assertEqual(estimate(value), 1)

    def test_empty_length_and_passphrases(self):
        self.assertEqual(estimate(''), 0)
        self.assertEqual(estimate('xY9!'), 1)
        self.assertEqual(estimate('fR8!kP2z'), 2)
        self.assertEqual(estimate('fR8!kP2zB6@q'), 3)
        self.assertEqual(estimate('fR8!kP2zB6@qH5$vN4#j'), 4)
        self.assertEqual(estimate('copper meadow lantern river'), 4)
