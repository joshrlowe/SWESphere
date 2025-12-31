import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../../core/theme/app_colors.dart';

/// Reusable avatar widget with image caching and fallback
class AvatarWidget extends StatelessWidget {
  final String? imageUrl;
  final String? name;
  final double size;
  final VoidCallback? onTap;
  final bool showBorder;
  final Color? borderColor;
  final double borderWidth;

  const AvatarWidget({
    super.key,
    this.imageUrl,
    this.name,
    this.size = 40,
    this.onTap,
    this.showBorder = false,
    this.borderColor,
    this.borderWidth = 2,
  });

  @override
  Widget build(BuildContext context) {
    Widget avatar = Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: AppColors.surface,
        border: showBorder
            ? Border.all(
                color: borderColor ?? AppColors.background,
                width: borderWidth,
              )
            : null,
      ),
      child: ClipOval(
        child: _buildContent(),
      ),
    );

    if (onTap != null) {
      return GestureDetector(
        onTap: onTap,
        child: avatar,
      );
    }

    return avatar;
  }

  Widget _buildContent() {
    if (imageUrl != null && imageUrl!.isNotEmpty) {
      return CachedNetworkImage(
        imageUrl: imageUrl!,
        fit: BoxFit.cover,
        width: size,
        height: size,
        placeholder: (context, url) => _buildPlaceholder(),
        errorWidget: (context, url, error) => _buildFallback(),
      );
    }

    return _buildFallback();
  }

  Widget _buildPlaceholder() {
    return Container(
      color: AppColors.surface,
      child: Center(
        child: SizedBox(
          width: size * 0.4,
          height: size * 0.4,
          child: const CircularProgressIndicator(
            strokeWidth: 2,
            color: AppColors.primary,
          ),
        ),
      ),
    );
  }

  Widget _buildFallback() {
    final initial = _getInitial();
    final fontSize = size * 0.4;

    return Container(
      color: _getAvatarColor(),
      child: Center(
        child: Text(
          initial,
          style: TextStyle(
            color: Colors.white,
            fontSize: fontSize,
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
    );
  }

  String _getInitial() {
    if (name != null && name!.isNotEmpty) {
      return name![0].toUpperCase();
    }
    return '?';
  }

  Color _getAvatarColor() {
    if (name == null || name!.isEmpty) {
      return AppColors.primary;
    }

    // Generate a consistent color based on the name
    final colors = [
      const Color(0xFF1DA1F2), // Twitter blue
      const Color(0xFFE91E63), // Pink
      const Color(0xFF9C27B0), // Purple
      const Color(0xFF673AB7), // Deep purple
      const Color(0xFF3F51B5), // Indigo
      const Color(0xFF2196F3), // Blue
      const Color(0xFF00BCD4), // Cyan
      const Color(0xFF009688), // Teal
      const Color(0xFF4CAF50), // Green
      const Color(0xFFFF9800), // Orange
    ];

    final index = name!.codeUnits.fold<int>(0, (a, b) => a + b) % colors.length;
    return colors[index];
  }
}

/// Group avatar for showing multiple users
class AvatarGroup extends StatelessWidget {
  final List<AvatarData> avatars;
  final double size;
  final int maxVisible;
  final double overlap;

  const AvatarGroup({
    super.key,
    required this.avatars,
    this.size = 32,
    this.maxVisible = 3,
    this.overlap = 0.3,
  });

  @override
  Widget build(BuildContext context) {
    final visibleAvatars = avatars.take(maxVisible).toList();
    final overflowCount = avatars.length - maxVisible;

    return SizedBox(
      height: size,
      width: size + (visibleAvatars.length - 1) * size * (1 - overlap) +
          (overflowCount > 0 ? size * (1 - overlap) : 0),
      child: Stack(
        children: [
          ...visibleAvatars.asMap().entries.map((entry) {
            return Positioned(
              left: entry.key * size * (1 - overlap),
              child: AvatarWidget(
                imageUrl: entry.value.imageUrl,
                name: entry.value.name,
                size: size,
                showBorder: true,
              ),
            );
          }),
          if (overflowCount > 0)
            Positioned(
              left: visibleAvatars.length * size * (1 - overlap),
              child: Container(
                width: size,
                height: size,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppColors.surface,
                  border: Border.all(
                    color: AppColors.background,
                    width: 2,
                  ),
                ),
                child: Center(
                  child: Text(
                    '+$overflowCount',
                    style: TextStyle(
                      fontSize: size * 0.35,
                      fontWeight: FontWeight.bold,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// Avatar data for group avatars
class AvatarData {
  final String? imageUrl;
  final String? name;

  const AvatarData({
    this.imageUrl,
    this.name,
  });
}

