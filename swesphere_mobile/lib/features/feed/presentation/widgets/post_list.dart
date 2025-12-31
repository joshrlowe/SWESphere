import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../../shared/widgets/post_card.dart';
import '../../domain/entities/post.dart';

/// Reusable post list widget with pull-to-refresh and infinite scroll
class PostList extends StatefulWidget {
  final List<Post> posts;
  final bool isLoading;
  final bool isLoadingMore;
  final bool hasMore;
  final String? error;
  final VoidCallback? onRefresh;
  final VoidCallback? onLoadMore;
  final void Function(Post post)? onLike;
  final void Function(Post post)? onReply;
  final void Function(Post post)? onRepost;
  final void Function(Post post)? onShare;
  final void Function(Post post)? onDelete;
  final void Function(Post post)? onTap;
  final Widget? emptyWidget;
  final Widget? errorWidget;

  const PostList({
    super.key,
    required this.posts,
    this.isLoading = false,
    this.isLoadingMore = false,
    this.hasMore = true,
    this.error,
    this.onRefresh,
    this.onLoadMore,
    this.onLike,
    this.onReply,
    this.onRepost,
    this.onShare,
    this.onDelete,
    this.onTap,
    this.emptyWidget,
    this.errorWidget,
  });

  @override
  State<PostList> createState() => _PostListState();
}

class _PostListState extends State<PostList> {
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      if (!widget.isLoadingMore && widget.hasMore) {
        widget.onLoadMore?.call();
      }
    }
  }

  Future<void> _handleRefresh() async {
    widget.onRefresh?.call();
    // Add a small delay for better UX
    await Future.delayed(const Duration(milliseconds: 500));
  }

  @override
  Widget build(BuildContext context) {
    // Loading state
    if (widget.isLoading && widget.posts.isEmpty) {
      return const Center(
        child: CircularProgressIndicator(color: AppColors.primary),
      );
    }

    // Error state
    if (widget.error != null && widget.posts.isEmpty) {
      return widget.errorWidget ?? _buildDefaultError(context);
    }

    // Empty state
    if (widget.posts.isEmpty) {
      return widget.emptyWidget ?? _buildDefaultEmpty(context);
    }

    // List
    return RefreshIndicator(
      onRefresh: _handleRefresh,
      color: AppColors.primary,
      backgroundColor: AppColors.surface,
      child: ListView.separated(
        controller: _scrollController,
        physics: const AlwaysScrollableScrollPhysics(),
        itemCount: widget.posts.length + (widget.hasMore ? 1 : 0),
        separatorBuilder: (context, index) => const Divider(height: 1),
        itemBuilder: (context, index) {
          // Loading more indicator
          if (index == widget.posts.length) {
            return _buildLoadingMore();
          }

          final post = widget.posts[index];
          return PostCard(
            post: post,
            onLike: widget.onLike != null ? () => widget.onLike!(post) : null,
            onReply: widget.onReply != null ? () => widget.onReply!(post) : null,
            onRepost: widget.onRepost != null ? () => widget.onRepost!(post) : null,
            onShare: widget.onShare != null ? () => widget.onShare!(post) : null,
            onDelete: widget.onDelete != null ? () => widget.onDelete!(post) : null,
          );
        },
      ),
    );
  }

  Widget _buildDefaultError(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.error_outline,
            size: 48,
            color: AppColors.error,
          ),
          const SizedBox(height: 16),
          Text(
            'Something went wrong',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            widget.error!,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppColors.textSecondary,
                ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: widget.onRefresh,
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  Widget _buildDefaultEmpty(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.article_outlined,
            size: 48,
            color: AppColors.textMuted,
          ),
          const SizedBox(height: 16),
          Text(
            'No posts yet',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            'Posts will appear here',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppColors.textSecondary,
                ),
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingMore() {
    return Container(
      padding: const EdgeInsets.all(24),
      alignment: Alignment.center,
      child: widget.isLoadingMore
          ? const CircularProgressIndicator(color: AppColors.primary)
          : const SizedBox.shrink(),
    );
  }
}

