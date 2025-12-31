import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/features/auth/domain/entities/user.dart';
import 'package:swesphere_mobile/features/auth/data/models/user_model.dart';
import 'package:swesphere_mobile/features/feed/domain/entities/post.dart';
import 'package:swesphere_mobile/features/feed/data/models/post_model.dart';
import 'package:swesphere_mobile/features/feed/domain/usecases/create_post.dart';

void main() {
  final testUser = User(
    id: 1,
    username: 'testuser',
    email: 'test@example.com',
    displayName: 'Test User',
    createdAt: DateTime.utc(2024, 1, 1),
  );

  group('Feed Flow Integration', () {
    test('Post entity -> PostModel JSON round-trip', () {
      // Create original post
      final originalPost = Post(
        id: 1,
        content: 'This is my first post! #flutter #testing',
        author: testUser,
        likesCount: 42,
        repliesCount: 7,
        repostsCount: 3,
        isLiked: true,
        isReposted: false,
        isBookmarked: true,
        mediaUrls: ['https://example.com/image1.jpg', 'https://example.com/image2.jpg'],
        createdAt: DateTime.utc(2024, 6, 15, 10, 30),
        updatedAt: DateTime.utc(2024, 6, 15, 11, 00),
      );

      // Create equivalent JSON
      final userJson = {
        'id': 1,
        'username': 'testuser',
        'email': 'test@example.com',
        'display_name': 'Test User',
        'created_at': '2024-01-01T00:00:00.000Z',
      };

      final postJson = {
        'id': 1,
        'content': 'This is my first post! #flutter #testing',
        'author': userJson,
        'likes_count': 42,
        'replies_count': 7,
        'reposts_count': 3,
        'is_liked': true,
        'is_reposted': false,
        'is_bookmarked': true,
        'media_urls': ['https://example.com/image1.jpg', 'https://example.com/image2.jpg'],
        'created_at': '2024-06-15T10:30:00.000Z',
        'updated_at': '2024-06-15T11:00:00.000Z',
      };

      // Parse JSON to model
      final model = PostModel.fromJson(postJson);

      // Convert to entity
      final restoredPost = model.toEntity();

      // Verify all fields match
      expect(restoredPost.id, originalPost.id);
      expect(restoredPost.content, originalPost.content);
      expect(restoredPost.author.username, originalPost.author.username);
      expect(restoredPost.likesCount, originalPost.likesCount);
      expect(restoredPost.repliesCount, originalPost.repliesCount);
      expect(restoredPost.repostsCount, originalPost.repostsCount);
      expect(restoredPost.isLiked, originalPost.isLiked);
      expect(restoredPost.isReposted, originalPost.isReposted);
      expect(restoredPost.isBookmarked, originalPost.isBookmarked);
      expect(restoredPost.mediaUrls, originalPost.mediaUrls);
    });

    test('CreatePostParams validation workflow', () {
      // Test valid post
      const validPost = CreatePostParams(
        content: 'Hello, SWESphere! 👋',
      );
      expect(validPost.validate(), isNull);
      expect(validPost.isValid, true);
      expect(validPost.remainingCharacters, 261);

      // Test empty post
      const emptyPost = CreatePostParams(content: '');
      expect(emptyPost.validate(), isNotNull);
      expect(emptyPost.isValid, false);

      // Test too long post
      final tooLongPost = CreatePostParams(content: 'a' * 300);
      expect(tooLongPost.validate(), isNotNull);
      expect(tooLongPost.isValid, false);
      expect(tooLongPost.remainingCharacters, -20);

      // Test max length post
      final maxLengthPost = CreatePostParams(content: 'a' * 280);
      expect(maxLengthPost.validate(), isNull);
      expect(maxLengthPost.isValid, true);
      expect(maxLengthPost.remainingCharacters, 0);
    });

    test('Reply post creation', () {
      const replyPost = CreatePostParams(
        content: 'Great point! I totally agree.',
        replyToId: 123,
      );

      expect(replyPost.replyToId, 123);
      expect(replyPost.isValid, true);
    });

    test('Post with media', () {
      const postWithMedia = CreatePostParams(
        content: 'Check out this photo!',
        mediaUrls: ['https://example.com/photo.jpg'],
      );

      expect(postWithMedia.mediaUrls, isNotNull);
      expect(postWithMedia.mediaUrls!.length, 1);
      expect(postWithMedia.isValid, true);
    });

    test('Post copyWith maintains data integrity', () {
      final originalPost = Post(
        id: 1,
        content: 'Original post',
        author: testUser,
        likesCount: 10,
        isLiked: false,
        createdAt: DateTime.utc(2024, 1, 1),
      );

      // Simulate like action
      final likedPost = originalPost.copyWith(
        isLiked: true,
        likesCount: 11,
      );

      expect(likedPost.isLiked, true);
      expect(likedPost.likesCount, 11);
      expect(likedPost.id, originalPost.id);
      expect(likedPost.content, originalPost.content);
      expect(likedPost.author, originalPost.author);

      // Simulate unlike action
      final unlikedPost = likedPost.copyWith(
        isLiked: false,
        likesCount: 10,
      );

      expect(unlikedPost.isLiked, false);
      expect(unlikedPost.likesCount, 10);
    });

    test('PaginatedPostsResponse parsing', () {
      final userJson = {
        'id': 1,
        'username': 'user1',
        'email': 'user1@test.com',
        'created_at': '2024-01-01T00:00:00.000Z',
      };

      final paginatedJson = {
        'items': [
          {
            'id': 1,
            'content': 'First post',
            'author': userJson,
            'created_at': '2024-01-01T00:00:00.000Z',
          },
          {
            'id': 2,
            'content': 'Second post',
            'author': userJson,
            'created_at': '2024-01-02T00:00:00.000Z',
          },
        ],
        'page': 1,
        'pages': 5,
        'total': 100,
        'has_next': true,
        'has_prev': false,
      };

      final response = PaginatedPostsResponse.fromJson(paginatedJson);

      expect(response.items.length, 2);
      expect(response.page, 1);
      expect(response.pages, 5);
      expect(response.total, 100);
      expect(response.hasNext, true);
      expect(response.hasPrev, false);
    });
  });
}

