import 'package:flutter/material.dart';

/// App color palette - Twitter/X inspired dark theme
abstract class AppColors {
  // ============================================================================
  // Primary Colors
  // ============================================================================
  
  /// Primary brand color - Twitter blue
  static const Color primary = Color(0xFF1DA1F2);
  
  /// Primary hover/pressed state
  static const Color primaryHover = Color(0xFF1A8CD8);
  
  /// Primary light (for backgrounds)
  static const Color primaryLight = Color(0x1A1DA1F2);
  
  // ============================================================================
  // Background Colors
  // ============================================================================
  
  /// Main background - pure black
  static const Color background = Color(0xFF000000);
  
  /// Elevated surface color
  static const Color surface = Color(0xFF16181C);
  
  /// Surface hover state
  static const Color surfaceHover = Color(0xFF1D1F23);
  
  /// Card background
  static const Color card = Color(0xFF16181C);
  
  /// Modal/overlay background
  static const Color overlay = Color(0xFF2F3336);
  
  // ============================================================================
  // Text Colors
  // ============================================================================
  
  /// Primary text color
  static const Color textPrimary = Color(0xFFE7E9EA);
  
  /// Secondary text color
  static const Color textSecondary = Color(0xFF71767B);
  
  /// Muted text color
  static const Color textMuted = Color(0xFF536471);
  
  // ============================================================================
  // Border Colors
  // ============================================================================
  
  /// Default border color
  static const Color border = Color(0xFF2F3336);
  
  /// Lighter border for inputs
  static const Color borderLight = Color(0xFF3E4144);
  
  // ============================================================================
  // Semantic Colors
  // ============================================================================
  
  /// Success/Green
  static const Color success = Color(0xFF00BA7C);
  
  /// Error/Red - for likes and errors
  static const Color error = Color(0xFFF4212E);
  
  /// Warning/Orange
  static const Color warning = Color(0xFFFFAD1F);
  
  /// Info/Blue
  static const Color info = Color(0xFF1DA1F2);
  
  // ============================================================================
  // Engagement Colors
  // ============================================================================
  
  /// Reply color
  static const Color reply = Color(0xFF1DA1F2);
  
  /// Repost color
  static const Color repost = Color(0xFF00BA7C);
  
  /// Like color
  static const Color like = Color(0xFFF91880);
  
  /// Share color
  static const Color share = Color(0xFF1DA1F2);
  
  // ============================================================================
  // Gradient
  // ============================================================================
  
  static const LinearGradient primaryGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [
      Color(0xFF1DA1F2),
      Color(0xFF1A8CD8),
    ],
  );
  
  // ============================================================================
  // Color Scheme
  // ============================================================================
  
  static ColorScheme get darkColorScheme => const ColorScheme.dark(
    primary: primary,
    onPrimary: Colors.white,
    secondary: primary,
    onSecondary: Colors.white,
    surface: surface,
    onSurface: textPrimary,
    background: background,
    onBackground: textPrimary,
    error: error,
    onError: Colors.white,
    outline: border,
  );
}

