import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import 'button_widget.dart';

/// Empty state types
enum EmptyStateType {
  posts,
  followers,
  following,
  notifications,
  messages,
  bookmarks,
  search,
  generic,
}

/// Empty state widget
class EmptyState extends StatelessWidget {
  final String? title;
  final String? message;
  final IconData? icon;
  final EmptyStateType type;
  final VoidCallback? onAction;
  final String? actionText;
  final double iconSize;

  const EmptyState({
    super.key,
    this.title,
    this.message,
    this.icon,
    this.type = EmptyStateType.generic,
    this.onAction,
    this.actionText,
    this.iconSize = 64,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon ?? _getIcon(),
              size: iconSize,
              color: AppColors.textMuted,
            ),
            const SizedBox(height: 24),
            Text(
              title ?? _getTitle(),
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              message ?? _getMessage(),
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSecondary,
                  ),
              textAlign: TextAlign.center,
            ),
            if (onAction != null && actionText != null) ...[
              const SizedBox(height: 24),
              AppButton(
                text: actionText!,
                onPressed: onAction,
                variant: ButtonVariant.primary,
              ),
            ],
          ],
        ),
      ),
    );
  }

  IconData _getIcon() {
    switch (type) {
      case EmptyStateType.posts:
        return Icons.article_outlined;
      case EmptyStateType.followers:
        return Icons.people_outline;
      case EmptyStateType.following:
        return Icons.person_add_outlined;
      case EmptyStateType.notifications:
        return Icons.notifications_none_outlined;
      case EmptyStateType.messages:
        return Icons.mail_outline;
      case EmptyStateType.bookmarks:
        return Icons.bookmark_outline;
      case EmptyStateType.search:
        return Icons.search_off;
      case EmptyStateType.generic:
        return Icons.inbox_outlined;
    }
  }

  String _getTitle() {
    switch (type) {
      case EmptyStateType.posts:
        return 'No posts yet';
      case EmptyStateType.followers:
        return 'No followers yet';
      case EmptyStateType.following:
        return 'Not following anyone';
      case EmptyStateType.notifications:
        return 'No notifications';
      case EmptyStateType.messages:
        return 'No messages';
      case EmptyStateType.bookmarks:
        return 'No bookmarks';
      case EmptyStateType.search:
        return 'No results found';
      case EmptyStateType.generic:
        return 'Nothing here';
    }
  }

  String _getMessage() {
    switch (type) {
      case EmptyStateType.posts:
        return 'When you or people you follow post, they\'ll show up here.';
      case EmptyStateType.followers:
        return 'When someone follows this account, they\'ll show up here.';
      case EmptyStateType.following:
        return 'When this account follows someone, they\'ll show up here.';
      case EmptyStateType.notifications:
        return 'When you get notifications, they\'ll show up here.';
      case EmptyStateType.messages:
        return 'When you get messages, they\'ll show up here.';
      case EmptyStateType.bookmarks:
        return 'Save posts for later by tapping the bookmark icon.';
      case EmptyStateType.search:
        return 'Try searching for something else.';
      case EmptyStateType.generic:
        return 'There\'s nothing to show here yet.';
    }
  }
}

/// Empty state for lists
class EmptyListState extends StatelessWidget {
  final EmptyStateType type;
  final VoidCallback? onAction;
  final String? actionText;

  const EmptyListState({
    super.key,
    this.type = EmptyStateType.generic,
    this.onAction,
    this.actionText,
  });

  @override
  Widget build(BuildContext context) {
    return EmptyState(
      type: type,
      onAction: onAction,
      actionText: actionText,
      iconSize: 48,
    );
  }
}

/// Search empty state
class SearchEmptyState extends StatelessWidget {
  final String query;
  final String? suggestion;

  const SearchEmptyState({
    super.key,
    required this.query,
    this.suggestion,
  });

  @override
  Widget build(BuildContext context) {
    return EmptyState(
      type: EmptyStateType.search,
      title: 'No results for "$query"',
      message: suggestion ?? 'Try searching for something else.',
    );
  }
}

/// Feed empty state with personalized message
class FeedEmptyState extends StatelessWidget {
  final VoidCallback? onExplore;

  const FeedEmptyState({super.key, this.onExplore});

  @override
  Widget build(BuildContext context) {
    return EmptyState(
      type: EmptyStateType.posts,
      title: 'Welcome to SWESphere!',
      message: 'Your feed is empty. Follow some people to see their posts here.',
      actionText: 'Explore',
      onAction: onExplore,
    );
  }
}

/// Profile posts empty state
class ProfilePostsEmptyState extends StatelessWidget {
  final bool isOwnProfile;
  final VoidCallback? onCreatePost;

  const ProfilePostsEmptyState({
    super.key,
    this.isOwnProfile = false,
    this.onCreatePost,
  });

  @override
  Widget build(BuildContext context) {
    if (isOwnProfile) {
      return EmptyState(
        icon: Icons.edit_outlined,
        title: 'Share your thoughts',
        message: 'Your posts will appear here. Start by creating your first post!',
        actionText: 'Create post',
        onAction: onCreatePost,
      );
    }

    return const EmptyState(
      type: EmptyStateType.posts,
      message: 'This user hasn\'t posted anything yet.',
    );
  }
}

