"""
Unit tests for validation logic, password policy, and auth helpers.
Run: python -m pytest tests/ -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import validate_password, validate_username


class TestPasswordValidation:
    def test_empty_password_rejected(self):
        valid, err = validate_password('')
        assert not valid
        assert 'wymagane' in err.lower()

    def test_short_password_rejected(self):
        valid, err = validate_password('abc')
        assert not valid
        assert '8' in err

    def test_7_char_password_rejected(self):
        valid, err = validate_password('abcdefg')
        assert not valid

    def test_8_char_no_complexity_rejected(self):
        valid, err = validate_password('abcdefgh')
        assert not valid
        assert 'cyfr' in err.lower() or 'wielk' in err.lower() or 'specjaln' in err.lower()

    def test_8_char_with_digit_accepted(self):
        valid, err = validate_password('abcdefg1')
        assert valid
        assert err is None

    def test_8_char_with_uppercase_accepted(self):
        valid, err = validate_password('abcdefgH')
        assert valid

    def test_8_char_with_special_accepted(self):
        valid, err = validate_password('abcdefg!')
        assert valid

    def test_max_length_128_accepted(self):
        valid, err = validate_password('A' + 'a' * 127)
        assert valid

    def test_over_128_rejected(self):
        valid, err = validate_password('A' + 'a' * 128)
        assert not valid
        assert '128' in err

    def test_none_password_rejected(self):
        valid, err = validate_password(None)
        assert not valid


class TestUsernameValidation:
    def test_empty_username_rejected(self):
        valid, err = validate_username('')
        assert not valid

    def test_short_username_rejected(self):
        valid, err = validate_username('ab')
        assert not valid

    def test_3_char_username_accepted(self):
        valid, err = validate_username('abc')
        assert valid

    def test_special_chars_rejected(self):
        valid, err = validate_username('user@name')
        assert not valid
        assert 'litery' in err.lower() or 'cyfry' in err.lower()

    def test_spaces_rejected(self):
        valid, err = validate_username('user name')
        assert not valid

    def test_long_username_rejected(self):
        valid, err = validate_username('a' * 21)
        assert not valid

    def test_20_char_username_accepted(self):
        valid, err = validate_username('a' * 20)
        assert valid

    def test_alphanumeric_accepted(self):
        valid, err = validate_username('Kuba123')
        assert valid


class TestPasswordHashing:
    def test_hash_and_verify(self):
        from database import hash_password, verify_password
        pw = 'TestPass1!'
        hashed = hash_password(pw)
        assert hashed != pw
        assert verify_password(pw, hashed)
        assert not verify_password('WrongPass1!', hashed)

    def test_verify_invalid_hash_returns_false(self):
        from database import verify_password
        assert not verify_password('anything', 'not_a_valid_hash')


class TestGymHours:
    def test_weekday_open_hours(self):
        from database import is_gym_open
        assert is_gym_open(0, 6)   # Monday 6am
        assert is_gym_open(0, 22)  # Monday 10pm
        assert is_gym_open(0, 23)  # Monday 11pm (open until midnight)
        assert not is_gym_open(0, 5)   # Monday 5am

    def test_weekend_open_hours(self):
        from database import is_gym_open
        assert is_gym_open(5, 8)   # Saturday 8am
        assert is_gym_open(5, 19)  # Saturday 7pm
        assert not is_gym_open(5, 7)   # Saturday 7am
        assert not is_gym_open(5, 20)  # Saturday 8pm

    def test_sunday(self):
        from database import is_gym_open
        assert is_gym_open(6, 10)  # Sunday 10am
        assert not is_gym_open(6, 7)  # Sunday 7am


class TestCompleteDayDetection:
    def test_empty_data_incomplete(self):
        from database import is_complete_day
        assert not is_complete_day({}, 0)

    def test_full_weekday_complete(self):
        from database import is_complete_day
        data = {h: 10 + h for h in range(6, 24)}  # 6-23 inclusive
        assert is_complete_day(data, 0)

    def test_too_many_missing_hours_incomplete(self):
        from database import is_complete_day
        data = {6: 10, 7: 15, 8: 20}  # missing most hours
        assert not is_complete_day(data, 0)

    def test_consecutive_zeros_incomplete(self):
        from database import is_complete_day
        data = {h: 0 if 10 <= h <= 14 else 20 for h in range(6, 24)}
        assert not is_complete_day(data, 0)
