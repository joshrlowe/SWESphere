import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/features/auth/data/models/user_model.dart';
import 'package:swesphere_mobile/features/feed/data/models/post_model.dart';
import 'package:swesphere_mobile/features/feed/domain/entities/post.dart';

void main() {
  final testUserJson = {
    'id': 1,
    'username': 'testuser',
    'email': 'test@example.com',
    'created_at': '2024-01-01T00:00:00.000Z',
  };

  final testPostJson = {
    'id': 1,
    'content': 'This is a test post',
    'author': testUserJson,
    'likes_count': 10,
    'replies_count': 5,
    'reposts_count': 2,
    'is_liked': true,
    'is_reposted': false,
    'is_bookmarked': false,
    'media_urls': ['https://example.com/image.jpg'],
    'created_at': '2024-01-15T12:00:00.000Z',
    'updated_at': null,
  };

  group('PostModel', () {
    group('fromJson', () {
      test('creates PostModel from valid JSON', () {
        final model = PostModel.fromJson(testPostJson);

        expect(model.id, 1);
        expect(model.content, 'This is a test post');
        expect(model.author, isA<UserModel>());
        expect(model.likesCount, 10);
        expect(model.repliesCount, 5);
        expect(model.repostsCount, 2);
        expect(model.isLiked, true);
        expect(model.isReposted, false);
        expect(model.isBookmarked, false);
        expect(model.mediaUrls, ['https://example.com/image.jpg']);
      });

      test('handles minimal JSON with defaults', () {
        final minimalJson = {
          'id': 1,
          'content': 'Minimal post',
          'author': testUserJson,
          'created_at': '2024-01-01T00:00:00.000Z',
        };

        final model = PostModel.fromJson(minimalJson);

        expect(model.id, 1);
        expect(model.content, 'Minimal post');
        expect(model.likesCount, 0);
        expect(model.repliesCount, 0);
        expect(model.repostsCount, 0);
        expect(model.isLiked, false);
        expect(model.isReposted, false);
        expect(model.isBookmarked, false);
        expect(model.mediaUrls, isNull);
        expect(model.replyTo, isNull);
        expect(model.repostOf, isNull);
      });

      test('handles nested reply_to', () {
        final replyJson = {
          'id': 2,
          'content': 'This is a reply',
          'author': testUserJson,
          'reply_to': testPostJson,
          'created_at': '2024-01-16T12:00:00.000Z',
        };

        final model = PostModel.fromJson(replyJson);

        expect(model.replyTo, isA<PostModel>());
        expect(model.replyTo!.id, 1);
        expect(model.replyTo!.content, 'This is a test post');
      });
    });

    group('toEntity', () {
      test('converts PostModel to Post entity', () {
        final model = PostModel.fromJson(testPostJson);
        final entity = model.toEntity();

        expect(entity, isA<Post>());
        expect(entity.id, 1);
        expect(entity.content, 'This is a test post');
        expect(entity.author.username, 'testuser');
        expect(entity.likesCount, 10);
        expect(entity.isLiked, true);
        expect(entity.mediaUrls, ['https://example.com/image.jpg']);
      });

      test('converts nested entities correctly', () {
        final replyJson = {
          'id': 2,
          'content': 'This is a reply',
          'author': testUserJson,
          'reply_to': testPostJson,
          'created_at': '2024-01-16T12:00:00.000Z',
        };

        final model = PostModel.fromJson(replyJson);
        final entity = model.toEntity();

        expect(entity.replyTo, isA<Post>());
        expect(entity.replyTo!.id, 1);
      });
    });
  });

  group('PaginatedPostsResponse', () {
    test('creates from JSON', () {
      final json = {
        'items': [testPostJson],
        'page': 1,
        'pages': 5,
        'total': 100,
        'has_next': true,
        'has_prev': false,
      };

      final response = PaginatedPostsResponse.fromJson(json);

      expect(response.items.length, 1);
      expect(response.items.first.content, 'This is a test post');
      expect(response.page, 1);
      expect(response.pages, 5);
      expect(response.total, 100);
      expect(response.hasNext, true);
      expect(response.hasPrev, false);
    });

    test('handles empty items list', () {
      final json = {
        'items': [],
        'page': 1,
        'pages': 0,
        'total': 0,
        'has_next': false,
        'has_prev': false,
      };

      final response = PaginatedPostsResponse.fromJson(json);

      expect(response.items, isEmpty);
      expect(response.total, 0);
    });
  });
}

