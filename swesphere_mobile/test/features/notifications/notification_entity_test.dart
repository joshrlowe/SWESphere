import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/features/auth/domain/entities/user.dart';
import 'package:swesphere_mobile/features/notifications/domain/entities/notification.dart';

void main() {
  group('AppNotification entity', () {
    final testActor = User(
      id: 1,
      username: 'actor',
      email: 'actor@example.com',
      displayName: 'Actor Name',
      createdAt: DateTime(2024, 1, 1),
    );

    test('creates like notification with correct message', () {
      final notification = AppNotification(
        id: 1,
        type: NotificationType.like,
        actor: testActor,
        postId: 123,
        postContent: 'This is the liked post content',
        createdAt: DateTime(2024, 1, 15),
      );

      expect(notification.type, NotificationType.like);
      expect(notification.message, 'liked your post');
      expect(notification.postId, 123);
      expect(notification.postContent, 'This is the liked post content');
    });

    test('creates reply notification with correct message', () {
      final notification = AppNotification(
        id: 2,
        type: NotificationType.reply,
        actor: testActor,
        postId: 456,
        createdAt: DateTime(2024, 1, 15),
      );

      expect(notification.type, NotificationType.reply);
      expect(notification.message, 'replied to your post');
    });

    test('creates follow notification with correct message', () {
      final notification = AppNotification(
        id: 3,
        type: NotificationType.follow,
        actor: testActor,
        createdAt: DateTime(2024, 1, 15),
      );

      expect(notification.type, NotificationType.follow);
      expect(notification.message, 'followed you');
      expect(notification.postId, isNull);
    });

    test('creates mention notification with correct message', () {
      final notification = AppNotification(
        id: 4,
        type: NotificationType.mention,
        actor: testActor,
        postId: 789,
        createdAt: DateTime(2024, 1, 15),
      );

      expect(notification.type, NotificationType.mention);
      expect(notification.message, 'mentioned you');
    });

    test('creates repost notification with correct message', () {
      final notification = AppNotification(
        id: 5,
        type: NotificationType.repost,
        actor: testActor,
        postId: 101,
        createdAt: DateTime(2024, 1, 15),
      );

      expect(notification.type, NotificationType.repost);
      expect(notification.message, 'reposted your post');
    });

    test('isRead defaults to false', () {
      final notification = AppNotification(
        id: 1,
        type: NotificationType.like,
        actor: testActor,
        createdAt: DateTime(2024, 1, 15),
      );

      expect(notification.isRead, false);
    });

    test('can create read notification', () {
      final notification = AppNotification(
        id: 1,
        type: NotificationType.like,
        actor: testActor,
        isRead: true,
        createdAt: DateTime(2024, 1, 15),
      );

      expect(notification.isRead, true);
    });

    test('copyWith creates new notification with updated fields', () {
      final notification = AppNotification(
        id: 1,
        type: NotificationType.like,
        actor: testActor,
        isRead: false,
        createdAt: DateTime(2024, 1, 15),
      );

      final updatedNotification = notification.copyWith(isRead: true);

      expect(updatedNotification.isRead, true);
      expect(updatedNotification.id, notification.id);
      expect(updatedNotification.type, notification.type);
    });

    test('equality works correctly', () {
      final notification1 = AppNotification(
        id: 1,
        type: NotificationType.like,
        actor: testActor,
        createdAt: DateTime(2024, 1, 15),
      );
      final notification2 = AppNotification(
        id: 1,
        type: NotificationType.like,
        actor: testActor,
        createdAt: DateTime(2024, 1, 15),
      );
      final notification3 = AppNotification(
        id: 2,
        type: NotificationType.follow,
        actor: testActor,
        createdAt: DateTime(2024, 1, 15),
      );

      expect(notification1, equals(notification2));
      expect(notification1, isNot(equals(notification3)));
    });
  });

  group('NotificationType', () {
    test('has all expected types', () {
      expect(NotificationType.values, contains(NotificationType.like));
      expect(NotificationType.values, contains(NotificationType.reply));
      expect(NotificationType.values, contains(NotificationType.follow));
      expect(NotificationType.values, contains(NotificationType.mention));
      expect(NotificationType.values, contains(NotificationType.repost));
      expect(NotificationType.values.length, 5);
    });
  });
}

