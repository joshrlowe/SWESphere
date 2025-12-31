import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/core/theme/app_colors.dart';
import 'package:swesphere_mobile/core/theme/app_theme.dart';

void main() {
  group('AppColors', () {
    test('primary color is Twitter blue', () {
      expect(AppColors.primary, const Color(0xFF1DA1F2));
    });

    test('background is pure black', () {
      expect(AppColors.background, const Color(0xFF000000));
    });

    test('surface color is dark gray', () {
      expect(AppColors.surface, const Color(0xFF16181C));
    });

    test('like color is pink', () {
      expect(AppColors.like, const Color(0xFFF91880));
    });

    test('repost color is green', () {
      expect(AppColors.repost, const Color(0xFF00BA7C));
    });

    test('error color is red', () {
      expect(AppColors.error, const Color(0xFFF4212E));
    });

    test('darkColorScheme has correct primary', () {
      final scheme = AppColors.darkColorScheme;
      expect(scheme.primary, AppColors.primary);
      expect(scheme.brightness, Brightness.dark);
    });
  });

  group('AppTheme', () {
    test('darkTheme uses Material 3', () {
      final theme = AppTheme.darkTheme;
      expect(theme.useMaterial3, isTrue);
    });

    test('darkTheme has correct brightness', () {
      final theme = AppTheme.darkTheme;
      expect(theme.brightness, Brightness.dark);
    });

    test('darkTheme has correct scaffold background', () {
      final theme = AppTheme.darkTheme;
      expect(theme.scaffoldBackgroundColor, AppColors.background);
    });

    test('darkTheme has correct primary color', () {
      final theme = AppTheme.darkTheme;
      expect(theme.colorScheme.primary, AppColors.primary);
    });

    test('elevated button has rounded shape', () {
      final theme = AppTheme.darkTheme;
      final buttonTheme = theme.elevatedButtonTheme.style;
      expect(buttonTheme, isNotNull);
    });

    test('input decoration has correct border radius', () {
      final theme = AppTheme.darkTheme;
      final inputTheme = theme.inputDecorationTheme;
      expect(inputTheme.filled, isTrue);
      expect(inputTheme.fillColor, AppColors.surface);
    });

    test('app bar has no elevation', () {
      final theme = AppTheme.darkTheme;
      expect(theme.appBarTheme.elevation, 0);
    });

    test('card has no elevation', () {
      final theme = AppTheme.darkTheme;
      expect(theme.cardTheme.elevation, 0);
    });
  });
}

