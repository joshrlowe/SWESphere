import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/features/profile/domain/usecases/update_profile.dart';

void main() {
  group('UpdateProfileParams', () {
    group('validate', () {
      test('returns null for valid params', () {
        const params = UpdateProfileParams(
          displayName: 'John Doe',
          bio: 'Software developer',
          location: 'San Francisco',
          website: 'https://example.com',
        );

        expect(params.validate(), isNull);
      });

      test('returns null for empty params', () {
        const params = UpdateProfileParams();
        expect(params.validate(), isNull);
      });

      test('returns error for display name exceeding max length', () {
        final params = UpdateProfileParams(
          displayName: 'a' * 51,
        );

        expect(
          params.validate(),
          'Display name must be less than 50 characters',
        );
      });

      test('accepts display name at max length', () {
        final params = UpdateProfileParams(
          displayName: 'a' * 50,
        );

        expect(params.validate(), isNull);
      });

      test('returns error for bio exceeding max length', () {
        final params = UpdateProfileParams(
          bio: 'a' * 161,
        );

        expect(
          params.validate(),
          'Bio must be less than 160 characters',
        );
      });

      test('accepts bio at max length', () {
        final params = UpdateProfileParams(
          bio: 'a' * 160,
        );

        expect(params.validate(), isNull);
      });

      test('returns error for location exceeding max length', () {
        final params = UpdateProfileParams(
          location: 'a' * 31,
        );

        expect(
          params.validate(),
          'Location must be less than 30 characters',
        );
      });

      test('returns error for website exceeding max length', () {
        final params = UpdateProfileParams(
          website: 'https://${'a' * 100}.com',
        );

        expect(
          params.validate(),
          'Website must be less than 100 characters',
        );
      });

      test('returns error for invalid website URL', () {
        const params = UpdateProfileParams(
          website: 'not a valid url',
        );

        expect(
          params.validate(),
          'Please enter a valid website URL',
        );
      });

      test('accepts valid website URLs', () {
        const validUrls = [
          'https://example.com',
          'http://example.com',
          'www.example.com',
          'example.com',
          'https://subdomain.example.com/path',
        ];

        for (final url in validUrls) {
          final params = UpdateProfileParams(website: url);
          expect(params.validate(), isNull, reason: 'Failed for URL: $url');
        }
      });

      test('allows empty website', () {
        const params = UpdateProfileParams(website: '');
        expect(params.validate(), isNull);
      });
    });

    group('maxLengths', () {
      test('has correct max display name length', () {
        expect(UpdateProfileParams.maxDisplayNameLength, 50);
      });

      test('has correct max bio length', () {
        expect(UpdateProfileParams.maxBioLength, 160);
      });

      test('has correct max location length', () {
        expect(UpdateProfileParams.maxLocationLength, 30);
      });

      test('has correct max website length', () {
        expect(UpdateProfileParams.maxWebsiteLength, 100);
      });
    });
  });
}

