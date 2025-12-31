import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/features/auth/domain/entities/user.dart';
import 'package:swesphere_mobile/features/feed/domain/entities/post.dart';

void main() {
  group('Post entity', () {
    final testAuthor = User(
      id: 1,
      username: 'author',
      email: 'author@example.com',
      displayName: 'Author Name',
      createdAt: DateTime(2024, 1, 1),
    );

    final testPost = Post(
      id: 1,
      content: 'Hello, world! This is a test post.',
      author: testAuthor,
      likesCount: 10,
      repliesCount: 5,
      repostsCount: 2,
      isLiked: true,
      isReposted: false,
      isBookmarked: true,
      mediaUrls: ['https://example.com/image.jpg'],
      createdAt: DateTime(2024, 1, 15),
      updatedAt: DateTime(2024, 1, 16),
    );

    test('creates post with all properties', () {
      expect(testPost.id, 1);
      expect(testPost.content, 'Hello, world! This is a test post.');
      expect(testPost.author.username, 'author');
      expect(testPost.likesCount, 10);
      expect(testPost.repliesCount, 5);
      expect(testPost.repostsCount, 2);
      expect(testPost.isLiked, true);
      expect(testPost.isReposted, false);
      expect(testPost.isBookmarked, true);
      expect(testPost.mediaUrls, ['https://example.com/image.jpg']);
    });

    test('default values are set correctly', () {
      final minimalPost = Post(
        id: 2,
        content: 'Minimal post',
        author: testAuthor,
        createdAt: DateTime(2024, 1, 1),
      );

      expect(minimalPost.likesCount, 0);
      expect(minimalPost.repliesCount, 0);
      expect(minimalPost.repostsCount, 0);
      expect(minimalPost.isLiked, false);
      expect(minimalPost.isReposted, false);
      expect(minimalPost.isBookmarked, false);
      expect(minimalPost.replyTo, isNull);
      expect(minimalPost.repostOf, isNull);
      expect(minimalPost.mediaUrls, isNull);
      expect(minimalPost.updatedAt, isNull);
    });

    test('copyWith creates new post with updated fields', () {
      final updatedPost = testPost.copyWith(
        isLiked: false,
        likesCount: 9,
      );

      expect(updatedPost.isLiked, false);
      expect(updatedPost.likesCount, 9);
      // Other fields unchanged
      expect(updatedPost.content, testPost.content);
      expect(updatedPost.author, testPost.author);
    });

    test('copyWith preserves original when no changes', () {
      final copiedPost = testPost.copyWith();
      expect(copiedPost, equals(testPost));
    });

    test('equality works correctly', () {
      final post1 = Post(
        id: 1,
        content: 'Same content',
        author: testAuthor,
        createdAt: DateTime(2024, 1, 1),
      );
      final post2 = Post(
        id: 1,
        content: 'Same content',
        author: testAuthor,
        createdAt: DateTime(2024, 1, 1),
      );
      final post3 = Post(
        id: 2,
        content: 'Different',
        author: testAuthor,
        createdAt: DateTime(2024, 1, 1),
      );

      expect(post1, equals(post2));
      expect(post1, isNot(equals(post3)));
    });

    test('handles reply posts', () {
      final originalPost = Post(
        id: 1,
        content: 'Original post',
        author: testAuthor,
        createdAt: DateTime(2024, 1, 1),
      );

      final replyPost = Post(
        id: 2,
        content: 'This is a reply',
        author: testAuthor,
        replyTo: originalPost,
        createdAt: DateTime(2024, 1, 2),
      );

      expect(replyPost.replyTo, isNotNull);
      expect(replyPost.replyTo!.id, 1);
      expect(replyPost.replyTo!.content, 'Original post');
    });

    test('handles reposted posts', () {
      final originalPost = Post(
        id: 1,
        content: 'Original post to repost',
        author: testAuthor,
        createdAt: DateTime(2024, 1, 1),
      );

      final repost = Post(
        id: 3,
        content: '',
        author: testAuthor,
        repostOf: originalPost,
        createdAt: DateTime(2024, 1, 3),
      );

      expect(repost.repostOf, isNotNull);
      expect(repost.repostOf!.id, 1);
    });

    test('handles multiple media URLs', () {
      final postWithMedia = Post(
        id: 4,
        content: 'Post with multiple images',
        author: testAuthor,
        mediaUrls: [
          'https://example.com/image1.jpg',
          'https://example.com/image2.jpg',
          'https://example.com/image3.jpg',
        ],
        createdAt: DateTime(2024, 1, 1),
      );

      expect(postWithMedia.mediaUrls, hasLength(3));
      expect(postWithMedia.mediaUrls![0], contains('image1'));
    });
  });
}

