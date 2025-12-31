import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/core/extensions/context_extensions.dart';

void main() {
  group('StringExtensions', () {
    group('capitalize', () {
      test('capitalizes first letter', () {
        expect('hello'.capitalize(), 'Hello');
      });

      test('handles already capitalized', () {
        expect('Hello'.capitalize(), 'Hello');
      });

      test('handles single character', () {
        expect('a'.capitalize(), 'A');
      });

      test('returns empty string for empty input', () {
        expect(''.capitalize(), '');
      });
    });

    group('truncate', () {
      test('truncates long string', () {
        expect('Hello, World!'.truncate(5), 'Hello...');
      });

      test('returns original if shorter than max', () {
        expect('Hi'.truncate(10), 'Hi');
      });

      test('returns original if equal to max', () {
        expect('Hello'.truncate(5), 'Hello');
      });
    });

    group('isValidEmail', () {
      test('returns true for valid email', () {
        expect('test@example.com'.isValidEmail, true);
        expect('user.name@domain.org'.isValidEmail, true);
        expect('user+tag@example.co.uk'.isValidEmail, true);
      });

      test('returns false for invalid email', () {
        expect('invalid'.isValidEmail, false);
        expect('invalid@'.isValidEmail, false);
        expect('@example.com'.isValidEmail, false);
        expect('test@.com'.isValidEmail, false);
      });
    });

    group('isValidUsername', () {
      test('returns true for valid username', () {
        expect('user123'.isValidUsername, true);
        expect('test_user'.isValidUsername, true);
        expect('User_123'.isValidUsername, true);
      });

      test('returns false for invalid username', () {
        expect('user@name'.isValidUsername, false);
        expect('user name'.isValidUsername, false);
        expect('user-name'.isValidUsername, false);
        expect('user.name'.isValidUsername, false);
      });
    });

    group('isValidUrl', () {
      test('returns true for valid URLs', () {
        expect('https://example.com'.isValidUrl, true);
        expect('http://example.com'.isValidUrl, true);
        expect('www.example.com'.isValidUrl, true);
        expect('example.com'.isValidUrl, true);
        expect('https://subdomain.example.com/path'.isValidUrl, true);
      });

      test('returns false for invalid URLs', () {
        expect('not a url'.isValidUrl, false);
        expect('ftp://example.com'.isValidUrl, false);
      });
    });
  });

  group('DateTimeExtensions', () {
    group('isToday', () {
      test('returns true for today', () {
        expect(DateTime.now().isToday, true);
      });

      test('returns false for yesterday', () {
        final yesterday = DateTime.now().subtract(const Duration(days: 1));
        expect(yesterday.isToday, false);
      });

      test('returns false for tomorrow', () {
        final tomorrow = DateTime.now().add(const Duration(days: 1));
        expect(tomorrow.isToday, false);
      });
    });

    group('isYesterday', () {
      test('returns true for yesterday', () {
        final yesterday = DateTime.now().subtract(const Duration(days: 1));
        expect(yesterday.isYesterday, true);
      });

      test('returns false for today', () {
        expect(DateTime.now().isYesterday, false);
      });
    });

    group('toRelativeString', () {
      test('returns "just now" for very recent', () {
        final now = DateTime.now();
        expect(now.toRelativeString(), 'just now');
      });

      test('returns minutes for under an hour', () {
        final thirtyMinsAgo = DateTime.now().subtract(const Duration(minutes: 30));
        expect(thirtyMinsAgo.toRelativeString(), '30m');
      });

      test('returns hours for under a day', () {
        final fiveHoursAgo = DateTime.now().subtract(const Duration(hours: 5));
        expect(fiveHoursAgo.toRelativeString(), '5h');
      });

      test('returns days for under a week', () {
        final threeDaysAgo = DateTime.now().subtract(const Duration(days: 3));
        expect(threeDaysAgo.toRelativeString(), '3d');
      });

      test('returns date for over a week', () {
        final twoWeeksAgo = DateTime.now().subtract(const Duration(days: 14));
        final result = twoWeeksAgo.toRelativeString();
        expect(result, contains('/'));
      });
    });
  });
}

