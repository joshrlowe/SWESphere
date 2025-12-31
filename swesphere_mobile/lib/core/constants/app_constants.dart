/// App constants
abstract class AppConstants {
  /// App name
  static const String appName = 'SWESphere';
  
  /// App version
  static const String appVersion = '1.0.0';
  
  /// Default page size for pagination
  static const int defaultPageSize = 20;
  
  /// Max post content length
  static const int maxPostLength = 280;
  
  /// Max display name length
  static const int maxDisplayNameLength = 50;
  
  /// Max bio length
  static const int maxBioLength = 160;
  
  /// Max username length
  static const int maxUsernameLength = 20;
  
  /// Min username length
  static const int minUsernameLength = 3;
  
  /// Min password length
  static const int minPasswordLength = 8;
  
  /// Avatar sizes
  static const double avatarSmall = 32.0;
  static const double avatarMedium = 48.0;
  static const double avatarLarge = 80.0;
  
  /// Animation durations
  static const Duration animationFast = Duration(milliseconds: 150);
  static const Duration animationNormal = Duration(milliseconds: 300);
  static const Duration animationSlow = Duration(milliseconds: 500);
  
  /// Debounce durations
  static const Duration debounceShort = Duration(milliseconds: 300);
  static const Duration debounceLong = Duration(milliseconds: 500);
  
  /// Cache durations
  static const Duration cacheDurationShort = Duration(minutes: 5);
  static const Duration cacheDurationMedium = Duration(minutes: 15);
  static const Duration cacheDurationLong = Duration(hours: 1);
}

/// Feature flags
abstract class FeatureFlags {
  /// Enable dark mode toggle
  static const bool enableDarkModeToggle = false;
  
  /// Enable push notifications
  static const bool enablePushNotifications = true;
  
  /// Enable analytics
  static const bool enableAnalytics = false;
  
  /// Enable crash reporting
  static const bool enableCrashReporting = true;
  
  /// Enable biometric auth
  static const bool enableBiometricAuth = true;
}
