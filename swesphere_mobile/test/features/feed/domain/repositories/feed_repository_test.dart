import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/features/feed/domain/repositories/feed_repository.dart';

void main() {
  group('PaginatedPosts', () {
    test('creates with all fields', () {
      final paginatedPosts = PaginatedPosts(
        posts: [],
        page: 1,
        totalPages: 5,
        total: 100,
        hasNext: true,
        hasPrev: false,
      );

      expect(paginatedPosts.page, 1);
      expect(paginatedPosts.totalPages, 5);
      expect(paginatedPosts.total, 100);
      expect(paginatedPosts.hasNext, true);
      expect(paginatedPosts.hasPrev, false);
    });
  });

  group('CreatePostData', () {
    test('creates with content only', () {
      const data = CreatePostData(content: 'Hello world!');

      expect(data.content, 'Hello world!');
      expect(data.replyToId, isNull);
      expect(data.mediaUrls, isNull);
    });

    test('creates with all fields', () {
      const data = CreatePostData(
        content: 'Reply to post',
        replyToId: 123,
        mediaUrls: ['https://example.com/image.jpg'],
      );

      expect(data.content, 'Reply to post');
      expect(data.replyToId, 123);
      expect(data.mediaUrls, ['https://example.com/image.jpg']);
    });
  });
}

