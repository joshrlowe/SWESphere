import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/core/constants/app_constants.dart';

void main() {
  group('AppConstants', () {
    test('appName is correct', () {
      expect(AppConstants.appName, 'SWESphere');
    });

    test('maxPostLength is 280', () {
      expect(AppConstants.maxPostLength, 280);
    });

    test('maxBioLength is 160', () {
      expect(AppConstants.maxBioLength, 160);
    });

    test('maxDisplayNameLength is 50', () {
      expect(AppConstants.maxDisplayNameLength, 50);
    });

    test('defaultPageSize is 20', () {
      expect(AppConstants.defaultPageSize, 20);
    });
  });

  group('HiveBoxes', () {
    test('has correct box names', () {
      expect(HiveBoxes.users, 'users');
      expect(HiveBoxes.posts, 'posts');
      expect(HiveBoxes.settings, 'settings');
      expect(HiveBoxes.drafts, 'drafts');
    });
  });

  group('Endpoints', () {
    test('auth endpoints are correct', () {
      expect(Endpoints.login, '/auth/login');
      expect(Endpoints.register, '/auth/register');
      expect(Endpoints.logout, '/auth/logout');
      expect(Endpoints.refresh, '/auth/refresh');
    });

    test('user endpoints are correct', () {
      expect(Endpoints.users, '/users');
      expect(Endpoints.me, '/users/me');
      expect(Endpoints.user('testuser'), '/users/testuser');
      expect(Endpoints.followers('testuser'), '/users/testuser/followers');
      expect(Endpoints.following('testuser'), '/users/testuser/following');
      expect(Endpoints.follow('testuser'), '/users/testuser/follow');
    });

    test('post endpoints are correct', () {
      expect(Endpoints.posts, '/posts');
      expect(Endpoints.feed, '/posts/feed');
      expect(Endpoints.explore, '/posts/explore');
      expect(Endpoints.post(123), '/posts/123');
      expect(Endpoints.postLike(123), '/posts/123/like');
      expect(Endpoints.postReplies(123), '/posts/123/replies');
    });

    test('notification endpoints are correct', () {
      expect(Endpoints.notifications, '/notifications');
      expect(Endpoints.unreadCount, '/notifications/unread-count');
      expect(Endpoints.markRead(456), '/notifications/456/read');
    });
  });
}

