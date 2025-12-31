import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/features/feed/domain/usecases/create_post.dart';

void main() {
  group('CreatePostParams', () {
    group('validate', () {
      test('returns null for valid content', () {
        const params = CreatePostParams(content: 'Hello, this is a test post!');
        expect(params.validate(), isNull);
      });

      test('returns error for empty content', () {
        const params = CreatePostParams(content: '');
        expect(params.validate(), 'Post content cannot be empty');
      });

      test('returns error for whitespace-only content', () {
        const params = CreatePostParams(content: '   \n\t  ');
        expect(params.validate(), 'Post content cannot be empty');
      });

      test('returns error for content exceeding max length', () {
        final longContent = 'a' * 281;
        final params = CreatePostParams(content: longContent);
        expect(params.validate(), 'Post must be less than 280 characters');
      });

      test('accepts content at max length', () {
        final maxContent = 'a' * 280;
        final params = CreatePostParams(content: maxContent);
        expect(params.validate(), isNull);
      });
    });

    group('remainingCharacters', () {
      test('calculates remaining characters correctly', () {
        const params = CreatePostParams(content: 'Hello');
        expect(params.remainingCharacters, 275);
      });

      test('returns negative for exceeded length', () {
        final longContent = 'a' * 290;
        final params = CreatePostParams(content: longContent);
        expect(params.remainingCharacters, -10);
      });

      test('returns max for empty content', () {
        const params = CreatePostParams(content: '');
        expect(params.remainingCharacters, 280);
      });
    });

    group('isValid', () {
      test('returns true for valid content', () {
        const params = CreatePostParams(content: 'Valid post');
        expect(params.isValid, true);
      });

      test('returns false for empty content', () {
        const params = CreatePostParams(content: '');
        expect(params.isValid, false);
      });

      test('returns false for too long content', () {
        final params = CreatePostParams(content: 'a' * 300);
        expect(params.isValid, false);
      });
    });

    group('maxContentLength', () {
      test('is 280 characters', () {
        expect(CreatePostParams.maxContentLength, 280);
      });
    });

    test('creates with reply', () {
      const params = CreatePostParams(
        content: 'This is a reply',
        replyToId: 123,
      );

      expect(params.content, 'This is a reply');
      expect(params.replyToId, 123);
    });

    test('creates with media', () {
      const params = CreatePostParams(
        content: 'Post with image',
        mediaUrls: ['https://example.com/image.jpg'],
      );

      expect(params.mediaUrls, ['https://example.com/image.jpg']);
    });
  });
}

