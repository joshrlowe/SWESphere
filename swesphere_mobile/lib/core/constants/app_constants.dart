/// App-wide constants
abstract class AppConstants {
  /// App name
  static const String appName = 'SWESphere';

  /// Max post length
  static const int maxPostLength = 280;

  /// Max bio length
  static const int maxBioLength = 160;

  /// Max display name length
  static const int maxDisplayNameLength = 50;

  /// Default page size for pagination
  static const int defaultPageSize = 20;

  /// Cache duration in hours
  static const int cacheDurationHours = 24;

  /// Image compression quality
  static const int imageQuality = 80;

  /// Max image size in MB
  static const int maxImageSizeMB = 5;
}

/// Storage box names for Hive
abstract class HiveBoxes {
  static const String users = 'users';
  static const String posts = 'posts';
  static const String settings = 'settings';
  static const String drafts = 'drafts';
}

/// API endpoints
abstract class Endpoints {
  // Auth
  static const String login = '/auth/login';
  static const String register = '/auth/register';
  static const String logout = '/auth/logout';
  static const String refresh = '/auth/refresh';

  // Users
  static const String users = '/users';
  static const String me = '/users/me';
  static String user(String username) => '/users/$username';
  static String followers(String username) => '/users/$username/followers';
  static String following(String username) => '/users/$username/following';
  static String follow(String username) => '/users/$username/follow';

  // Posts
  static const String posts = '/posts';
  static const String feed = '/posts/feed';
  static const String explore = '/posts/explore';
  static String post(int id) => '/posts/$id';
  static String postLike(int id) => '/posts/$id/like';
  static String postReplies(int id) => '/posts/$id/replies';

  // Notifications
  static const String notifications = '/notifications';
  static const String unreadCount = '/notifications/unread-count';
  static String markRead(int id) => '/notifications/$id/read';
}

