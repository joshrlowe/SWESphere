import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/router/app_router.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../shared/widgets/avatar_widget.dart';
import '../../../auth/domain/entities/user.dart';
import 'follow_button.dart';

/// User list item (for followers/following lists)
class UserListItem extends StatelessWidget {
  final User user;
  final bool showFollowButton;
  final VoidCallback? onFollowPressed;
  final VoidCallback? onTap;

  const UserListItem({
    super.key,
    required this.user,
    this.showFollowButton = true,
    this.onFollowPressed,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap ?? () => context.push(AppRoutes.profileRoute(user.username)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Avatar
            AvatarWidget(
              imageUrl: user.avatarUrl,
              name: user.name,
              size: 48,
            ),
            const SizedBox(width: 12),

            // User info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Name and verified
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          user.name,
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (user.isVerified) ...[
                        const SizedBox(width: 4),
                        const Icon(
                          Icons.verified,
                          size: 16,
                          color: AppColors.primary,
                        ),
                      ],
                    ],
                  ),

                  // Handle
                  Text(
                    user.handle,
                    style: TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 14,
                    ),
                  ),

                  // Bio
                  if (user.bio != null && user.bio!.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      user.bio!,
                      style: Theme.of(context).textTheme.bodySmall,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ],
              ),
            ),

            // Follow button
            if (showFollowButton) ...[
              const SizedBox(width: 12),
              SmallFollowButton(
                isFollowing: user.isFollowing,
                onPressed: onFollowPressed,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Compact user tile for suggestions
class CompactUserTile extends StatelessWidget {
  final User user;
  final VoidCallback? onFollowPressed;

  const CompactUserTile({
    super.key,
    required this.user,
    this.onFollowPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 150,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          // Avatar
          AvatarWidget(
            imageUrl: user.avatarUrl,
            name: user.name,
            size: 56,
          ),
          const SizedBox(height: 8),

          // Name
          Text(
            user.name,
            style: const TextStyle(fontWeight: FontWeight.bold),
            overflow: TextOverflow.ellipsis,
          ),

          // Handle
          Text(
            user.handle,
            style: TextStyle(
              color: AppColors.textSecondary,
              fontSize: 13,
            ),
            overflow: TextOverflow.ellipsis,
          ),

          const SizedBox(height: 12),

          // Follow button
          SizedBox(
            width: double.infinity,
            child: SmallFollowButton(
              isFollowing: user.isFollowing,
              onPressed: onFollowPressed,
            ),
          ),
        ],
      ),
    );
  }
}

