import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:timeago/timeago.dart' as timeago;

import '../../core/router/app_router.dart';
import '../../core/theme/app_colors.dart';
import '../../features/feed/domain/entities/post.dart';

class PostCard extends StatefulWidget {
  final Post post;
  final VoidCallback? onLike;
  final VoidCallback? onReply;
  final VoidCallback? onRepost;
  final VoidCallback? onShare;
  final VoidCallback? onDelete;

  const PostCard({
    super.key,
    required this.post,
    this.onLike,
    this.onReply,
    this.onRepost,
    this.onShare,
    this.onDelete,
  });

  @override
  State<PostCard> createState() => _PostCardState();
}

class _PostCardState extends State<PostCard> with SingleTickerProviderStateMixin {
  late AnimationController _likeAnimationController;
  late Animation<double> _likeAnimation;

  @override
  void initState() {
    super.initState();
    _likeAnimationController = AnimationController(
      duration: const Duration(milliseconds: 200),
      vsync: this,
    );
    _likeAnimation = Tween<double>(begin: 1.0, end: 1.3).animate(
      CurvedAnimation(
        parent: _likeAnimationController,
        curve: Curves.easeInOut,
      ),
    );
  }

  @override
  void dispose() {
    _likeAnimationController.dispose();
    super.dispose();
  }

  void _handleLike() {
    if (!widget.post.isLiked) {
      _likeAnimationController.forward().then((_) {
        _likeAnimationController.reverse();
      });
    }
    widget.onLike?.call();
  }

  @override
  Widget build(BuildContext context) {
    final post = widget.post;
    final author = post.author;

    return InkWell(
      onTap: () {
        // TODO: Navigate to post detail
      },
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Avatar
            GestureDetector(
              onTap: () => context.push(AppRoutes.profileRoute(author.username)),
              child: CircleAvatar(
                radius: 24,
                backgroundColor: AppColors.surface,
                backgroundImage: author.avatarUrl != null
                    ? NetworkImage(author.avatarUrl!)
                    : null,
                child: author.avatarUrl == null
                    ? Text(
                        author.name[0].toUpperCase(),
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      )
                    : null,
              ),
            ),
            const SizedBox(width: 12),

            // Content
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Header
                  Row(
                    children: [
                      // Name
                      Flexible(
                        child: GestureDetector(
                          onTap: () => context.push(
                            AppRoutes.profileRoute(author.username),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Flexible(
                                child: Text(
                                  author.name,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                              if (author.isVerified) ...[
                                const SizedBox(width: 4),
                                const Icon(
                                  Icons.verified,
                                  size: 16,
                                  color: AppColors.primary,
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(width: 4),
                      Text(
                        '@${author.username}',
                        style: TextStyle(color: AppColors.textSecondary),
                      ),
                      const Text(' · ', style: TextStyle(color: AppColors.textSecondary)),
                      Text(
                        timeago.format(post.createdAt, locale: 'en_short'),
                        style: TextStyle(color: AppColors.textSecondary),
                      ),
                      const Spacer(),
                      // More menu
                      PopupMenuButton<String>(
                        icon: Icon(
                          Icons.more_horiz,
                          color: AppColors.textSecondary,
                          size: 20,
                        ),
                        onSelected: (value) {
                          if (value == 'delete') {
                            widget.onDelete?.call();
                          }
                        },
                        itemBuilder: (context) => [
                          const PopupMenuItem(
                            value: 'delete',
                            child: Row(
                              children: [
                                Icon(Icons.delete_outline, color: AppColors.error),
                                SizedBox(width: 8),
                                Text(
                                  'Delete',
                                  style: TextStyle(color: AppColors.error),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),

                  // Content
                  const SizedBox(height: 4),
                  Text(
                    post.content,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),

                  // Media (if any)
                  if (post.mediaUrls != null && post.mediaUrls!.isNotEmpty) ...[
                    const SizedBox(height: 12),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: Image.network(
                        post.mediaUrls!.first,
                        fit: BoxFit.cover,
                        errorBuilder: (context, error, stack) => Container(
                          height: 200,
                          color: AppColors.surface,
                          child: const Center(
                            child: Icon(Icons.broken_image_outlined),
                          ),
                        ),
                      ),
                    ),
                  ],

                  // Actions
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      // Reply
                      _ActionButton(
                        icon: Icons.chat_bubble_outline,
                        count: post.repliesCount,
                        onTap: widget.onReply,
                      ),

                      // Repost
                      _ActionButton(
                        icon: Icons.repeat,
                        count: post.repostsCount,
                        color: post.isReposted ? AppColors.repost : null,
                        onTap: widget.onRepost,
                      ),

                      // Like
                      ScaleTransition(
                        scale: _likeAnimation,
                        child: _ActionButton(
                          icon: post.isLiked
                              ? Icons.favorite
                              : Icons.favorite_border,
                          count: post.likesCount,
                          color: post.isLiked ? AppColors.like : null,
                          onTap: _handleLike,
                        ),
                      ),

                      // Share
                      _ActionButton(
                        icon: Icons.share_outlined,
                        onTap: widget.onShare,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final int? count;
  final Color? color;
  final VoidCallback? onTap;

  const _ActionButton({
    required this.icon,
    this.count,
    this.color,
    this.onTap,
  });

  String _formatCount(int count) {
    if (count >= 1000000) {
      return '${(count / 1000000).toStringAsFixed(1)}M';
    } else if (count >= 1000) {
      return '${(count / 1000).toStringAsFixed(1)}K';
    }
    return count.toString();
  }

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        child: Row(
          children: [
            Icon(
              icon,
              size: 18,
              color: color ?? AppColors.textSecondary,
            ),
            if (count != null && count! > 0) ...[
              const SizedBox(width: 4),
              Text(
                _formatCount(count!),
                style: TextStyle(
                  fontSize: 13,
                  color: color ?? AppColors.textSecondary,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

