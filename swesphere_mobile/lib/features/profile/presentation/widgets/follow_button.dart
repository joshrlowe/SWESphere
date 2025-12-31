import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';

/// Animated follow button
class FollowButton extends StatefulWidget {
  final bool isFollowing;
  final bool isLoading;
  final VoidCallback? onPressed;
  final bool compact;

  const FollowButton({
    super.key,
    required this.isFollowing,
    this.isLoading = false,
    this.onPressed,
    this.compact = false,
  });

  @override
  State<FollowButton> createState() => _FollowButtonState();
}

class _FollowButtonState extends State<FollowButton>
    with SingleTickerProviderStateMixin {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    if (widget.isFollowing) {
      return _buildFollowingButton();
    }

    return _buildFollowButton();
  }

  Widget _buildFollowButton() {
    return SizedBox(
      height: widget.compact ? 32 : 36,
      child: ElevatedButton(
        onPressed: widget.isLoading ? null : widget.onPressed,
        style: ElevatedButton.styleFrom(
          padding: EdgeInsets.symmetric(
            horizontal: widget.compact ? 12 : 16,
          ),
        ),
        child: widget.isLoading
            ? SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.white,
                ),
              )
            : Text(
                'Follow',
                style: TextStyle(
                  fontSize: widget.compact ? 13 : 14,
                  fontWeight: FontWeight.bold,
                ),
              ),
      ),
    );
  }

  Widget _buildFollowingButton() {
    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: SizedBox(
        height: widget.compact ? 32 : 36,
        child: OutlinedButton(
          onPressed: widget.isLoading ? null : widget.onPressed,
          style: OutlinedButton.styleFrom(
            padding: EdgeInsets.symmetric(
              horizontal: widget.compact ? 12 : 16,
            ),
            side: BorderSide(
              color: _isHovered ? AppColors.error : AppColors.border,
            ),
          ),
          child: widget.isLoading
              ? SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: AppColors.textPrimary,
                  ),
                )
              : Text(
                  _isHovered ? 'Unfollow' : 'Following',
                  style: TextStyle(
                    fontSize: widget.compact ? 13 : 14,
                    fontWeight: FontWeight.bold,
                    color: _isHovered ? AppColors.error : AppColors.textPrimary,
                  ),
                ),
        ),
      ),
    );
  }
}

/// Small follow button for lists
class SmallFollowButton extends StatelessWidget {
  final bool isFollowing;
  final bool isLoading;
  final VoidCallback? onPressed;

  const SmallFollowButton({
    super.key,
    required this.isFollowing,
    this.isLoading = false,
    this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return FollowButton(
      isFollowing: isFollowing,
      isLoading: isLoading,
      onPressed: onPressed,
      compact: true,
    );
  }
}

