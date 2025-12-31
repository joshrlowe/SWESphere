import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:intl/intl.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../auth/domain/entities/user.dart';
import '../../../../shared/widgets/avatar_widget.dart';

/// Profile header widget
class ProfileHeader extends StatelessWidget {
  final User user;
  final bool isOwnProfile;
  final VoidCallback? onEditProfile;
  final VoidCallback? onFollow;
  final VoidCallback? onFollowersPressed;
  final VoidCallback? onFollowingPressed;

  const ProfileHeader({
    super.key,
    required this.user,
    this.isOwnProfile = false,
    this.onEditProfile,
    this.onFollow,
    this.onFollowersPressed,
    this.onFollowingPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Banner
        _buildBanner(),

        Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Avatar and action button
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  // Avatar (overlapping banner)
                  Transform.translate(
                    offset: const Offset(0, -50),
                    child: Container(
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: AppColors.background,
                          width: 4,
                        ),
                      ),
                      child: AvatarWidget(
                        imageUrl: user.avatarUrl,
                        name: user.name,
                        size: 80,
                      ),
                    ),
                  ),

                  // Action button
                  if (isOwnProfile)
                    OutlinedButton(
                      onPressed: onEditProfile,
                      child: const Text('Edit profile'),
                    )
                  else
                    _buildFollowButton(),
                ],
              ),

              // Name and handle (adjusted for avatar offset)
              Transform.translate(
                offset: const Offset(0, -30),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Name with verified badge
                    Row(
                      children: [
                        Flexible(
                          child: Text(
                            user.name,
                            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                                  fontWeight: FontWeight.bold,
                                ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        if (user.isVerified) ...[
                          const SizedBox(width: 4),
                          const Icon(
                            Icons.verified,
                            color: AppColors.primary,
                            size: 20,
                          ),
                        ],
                      ],
                    ),
                    Text(
                      user.handle,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: AppColors.textSecondary,
                          ),
                    ),

                    const SizedBox(height: 12),

                    // Bio
                    if (user.bio != null && user.bio!.isNotEmpty)
                      Text(
                        user.bio!,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),

                    const SizedBox(height: 12),

                    // Location, website, join date
                    _buildInfoRow(context),

                    const SizedBox(height: 12),

                    // Stats
                    _buildStats(context),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildBanner() {
    return SizedBox(
      height: 150,
      width: double.infinity,
      child: user.bannerUrl != null
          ? CachedNetworkImage(
              imageUrl: user.bannerUrl!,
              fit: BoxFit.cover,
              placeholder: (context, url) => Container(
                color: AppColors.primary.withOpacity(0.3),
              ),
              errorWidget: (context, url, error) => Container(
                color: AppColors.primary.withOpacity(0.3),
              ),
            )
          : Container(
              color: AppColors.primary.withOpacity(0.3),
            ),
    );
  }

  Widget _buildFollowButton() {
    if (user.isFollowing) {
      return OutlinedButton(
        onPressed: onFollow,
        child: const Text('Following'),
      );
    }

    return ElevatedButton(
      onPressed: onFollow,
      child: const Text('Follow'),
    );
  }

  Widget _buildInfoRow(BuildContext context) {
    final items = <Widget>[];

    if (user.location != null && user.location!.isNotEmpty) {
      items.add(_buildInfoItem(
        context,
        Icons.location_on_outlined,
        user.location!,
      ));
    }

    if (user.website != null && user.website!.isNotEmpty) {
      items.add(_buildInfoItem(
        context,
        Icons.link,
        user.website!,
        isLink: true,
      ));
    }

    items.add(_buildInfoItem(
      context,
      Icons.calendar_today_outlined,
      'Joined ${DateFormat.yMMMM().format(user.createdAt)}',
    ));

    return Wrap(
      spacing: 16,
      runSpacing: 4,
      children: items,
    );
  }

  Widget _buildInfoItem(
    BuildContext context,
    IconData icon,
    String text, {
    bool isLink = false,
  }) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          icon,
          size: 16,
          color: AppColors.textSecondary,
        ),
        const SizedBox(width: 4),
        Text(
          text,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: isLink ? AppColors.primary : AppColors.textSecondary,
              ),
        ),
      ],
    );
  }

  Widget _buildStats(BuildContext context) {
    return Row(
      children: [
        GestureDetector(
          onTap: onFollowingPressed,
          child: _buildStatItem(context, user.followingCount, 'Following'),
        ),
        const SizedBox(width: 24),
        GestureDetector(
          onTap: onFollowersPressed,
          child: _buildStatItem(context, user.followersCount, 'Followers'),
        ),
      ],
    );
  }

  Widget _buildStatItem(BuildContext context, int count, String label) {
    return Row(
      children: [
        Text(
          _formatCount(count),
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: AppColors.textSecondary,
              ),
        ),
      ],
    );
  }

  String _formatCount(int count) {
    if (count >= 1000000) {
      return '${(count / 1000000).toStringAsFixed(1)}M';
    } else if (count >= 1000) {
      return '${(count / 1000).toStringAsFixed(1)}K';
    }
    return count.toString();
  }
}

