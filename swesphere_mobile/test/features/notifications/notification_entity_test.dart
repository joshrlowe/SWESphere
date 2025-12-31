import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/features/auth/domain/entities/user.dart';
import 'package:swesphere_mobile/features/notifications/domain/entities/notification.dart';

void main() {
  final testUser = User(
    id: 1,
    username: 'testuser',
    email: 'test@example.com',
    displayName: 'Test User',
    createdAt: DateTime(2024, 1, 1),
  );

  group('NotificationType', () {
    test('has all expected values', () {
      expect(NotificationType.values, contains(NotificationType.like));
      expect(NotificationType.values, contains(NotificationType.reply));
      expect(NotificationType.values, contains(NotificationType.repost));
      expect(NotificationType.values, contains(NotificationType.follow));
      expect(NotificationType.values, contains(NotificationType.mention));
      expect(NotificationType.values, contains(NotificationType.quote));
    });
  });

  group('AppNotification', () {
    test('creates with required fields', () {
      final notification = AppNotification(
        id: 1,
        type: NotificationType.like,
        fromUser: testUser,
        createdAt: DateTime(2024, 1, 15),
      );

      expect(notification.id, 1);
      expect(notification.type, NotificationType.like);
      expect(notification.fromUser, testUser);
      expect(notification.postId, isNull);
      expect(notification.postContent, isNull);
      expect(notification.isRead, false);
    });

    test('creates with all fields', () {
      final notification = AppNotification(
        id: 1,
        type: NotificationType.reply,
        fromUser: testUser,
        postId: 123,
        postContent: 'This is the post content',
        isRead: true,
        createdAt: DateTime(2024, 1, 15),
      );

      expect(notification.postId, 123);
      expect(notification.postContent, 'This is the post content');
      expect(notification.isRead, true);
    });

    group('message', () {
      test('returns correct message for like', () {
        final notification = AppNotification(
          id: 1,
          type: NotificationType.like,
          fromUser: testUser,
          createdAt: DateTime(2024, 1, 15),
        );

        expect(notification.message, 'Test User liked your post');
      });

      test('returns correct message for reply', () {
        final notification = AppNotification(
          id: 1,
          type: NotificationType.reply,
          fromUser: testUser,
          createdAt: DateTime(2024, 1, 15),
        );

        expect(notification.message, 'Test User replied to your post');
      });

      test('returns correct message for repost', () {
        final notification = AppNotification(
          id: 1,
          type: NotificationType.repost,
          fromUser: testUser,
          createdAt: DateTime(2024, 1, 15),
        );

        expect(notification.message, 'Test User reposted your post');
      });

      test('returns correct message for follow', () {
        final notification = AppNotification(
          id: 1,
          type: NotificationType.follow,
          fromUser: testUser,
          createdAt: DateTime(2024, 1, 15),
        );

        expect(notification.message, 'Test User followed you');
      });

      test('returns correct message for mention', () {
        final notification = AppNotification(
          id: 1,
          type: NotificationType.mention,
          fromUser: testUser,
          createdAt: DateTime(2024, 1, 15),
        );

        expect(notification.message, 'Test User mentioned you');
      });

      test('returns correct message for quote', () {
        final notification = AppNotification(
          id: 1,
          type: NotificationType.quote,
          fromUser: testUser,
          createdAt: DateTime(2024, 1, 15),
        );

        expect(notification.message, 'Test User quoted your post');
      });
    });

    test('copyWith updates specified fields', () {
      final notification = AppNotification(
        id: 1,
        type: NotificationType.like,
        fromUser: testUser,
        isRead: false,
        createdAt: DateTime(2024, 1, 15),
      );

      final updated = notification.copyWith(isRead: true);

      expect(updated.isRead, true);
      expect(updated.id, 1);
      expect(updated.type, NotificationType.like);
    });

    test('equality works correctly', () {
      final notification1 = AppNotification(
        id: 1,
        type: NotificationType.like,
        fromUser: testUser,
        createdAt: DateTime(2024, 1, 15),
      );

      final notification2 = AppNotification(
        id: 1,
        type: NotificationType.like,
        fromUser: testUser,
        createdAt: DateTime(2024, 1, 15),
      );

      final notification3 = AppNotification(
        id: 2,
        type: NotificationType.follow,
        fromUser: testUser,
        createdAt: DateTime(2024, 1, 15),
      );

      expect(notification1, equals(notification2));
      expect(notification1, isNot(equals(notification3)));
    });
  });
}
