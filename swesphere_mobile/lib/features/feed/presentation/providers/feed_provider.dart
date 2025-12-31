import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../data/models/post_model.dart';
import '../../domain/entities/post.dart';

/// Feed state
class FeedState {
  final List<Post> posts;
  final bool isLoading;
  final bool isLoadingMore;
  final bool hasMore;
  final int currentPage;
  final String? error;

  const FeedState({
    this.posts = const [],
    this.isLoading = false,
    this.isLoadingMore = false,
    this.hasMore = true,
    this.currentPage = 1,
    this.error,
  });

  FeedState copyWith({
    List<Post>? posts,
    bool? isLoading,
    bool? isLoadingMore,
    bool? hasMore,
    int? currentPage,
    String? error,
  }) {
    return FeedState(
      posts: posts ?? this.posts,
      isLoading: isLoading ?? this.isLoading,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
      hasMore: hasMore ?? this.hasMore,
      currentPage: currentPage ?? this.currentPage,
      error: error,
    );
  }
}

/// Feed provider
final feedProvider = StateNotifierProvider<FeedNotifier, FeedState>((ref) {
  return FeedNotifier(
    apiClient: ref.watch(apiClientProvider),
  );
});

/// Feed notifier
class FeedNotifier extends StateNotifier<FeedState> {
  final ApiClient _apiClient;

  FeedNotifier({required ApiClient apiClient})
      : _apiClient = apiClient,
        super(const FeedState()) {
    loadFeed();
  }

  /// Load initial feed
  Future<void> loadFeed() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await _apiClient.get(
        '/posts/feed',
        queryParameters: {'page': 1, 'size': 20},
      );

      final data = PaginatedPostsResponse.fromJson(
        response.data as Map<String, dynamic>,
      );

      state = state.copyWith(
        posts: data.items.map((p) => p.toEntity()).toList(),
        isLoading: false,
        hasMore: data.hasNext,
        currentPage: data.page,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Load more posts (pagination)
  Future<void> loadMore() async {
    if (state.isLoadingMore || !state.hasMore) return;

    state = state.copyWith(isLoadingMore: true);

    try {
      final nextPage = state.currentPage + 1;
      final response = await _apiClient.get(
        '/posts/feed',
        queryParameters: {'page': nextPage, 'size': 20},
      );

      final data = PaginatedPostsResponse.fromJson(
        response.data as Map<String, dynamic>,
      );

      final newPosts = data.items.map((p) => p.toEntity()).toList();

      state = state.copyWith(
        posts: [...state.posts, ...newPosts],
        isLoadingMore: false,
        hasMore: data.hasNext,
        currentPage: data.page,
      );
    } catch (e) {
      state = state.copyWith(
        isLoadingMore: false,
        error: e.toString(),
      );
    }
  }

  /// Refresh feed
  Future<void> refresh() async {
    state = state.copyWith(currentPage: 1, hasMore: true);
    await loadFeed();
  }

  /// Like/unlike a post
  Future<void> toggleLike(int postId) async {
    final postIndex = state.posts.indexWhere((p) => p.id == postId);
    if (postIndex == -1) return;

    final post = state.posts[postIndex];
    final isLiked = post.isLiked;

    // Optimistic update
    final updatedPost = post.copyWith(
      isLiked: !isLiked,
      likesCount: isLiked ? post.likesCount - 1 : post.likesCount + 1,
    );

    final updatedPosts = [...state.posts];
    updatedPosts[postIndex] = updatedPost;
    state = state.copyWith(posts: updatedPosts);

    try {
      if (isLiked) {
        await _apiClient.delete('/posts/$postId/like');
      } else {
        await _apiClient.post('/posts/$postId/like');
      }
    } catch (e) {
      // Revert on error
      final revertedPosts = [...state.posts];
      revertedPosts[postIndex] = post;
      state = state.copyWith(posts: revertedPosts);
    }
  }

  /// Create a new post
  Future<void> createPost(String content) async {
    try {
      final response = await _apiClient.post(
        '/posts',
        data: {'content': content},
      );

      final newPost = PostModel.fromJson(
        response.data as Map<String, dynamic>,
      ).toEntity();

      // Add to beginning of feed
      state = state.copyWith(
        posts: [newPost, ...state.posts],
      );
    } catch (e) {
      rethrow;
    }
  }

  /// Delete a post
  Future<void> deletePost(int postId) async {
    final postIndex = state.posts.indexWhere((p) => p.id == postId);
    if (postIndex == -1) return;

    final post = state.posts[postIndex];

    // Optimistic delete
    final updatedPosts = state.posts.where((p) => p.id != postId).toList();
    state = state.copyWith(posts: updatedPosts);

    try {
      await _apiClient.delete('/posts/$postId');
    } catch (e) {
      // Revert on error
      final revertedPosts = [...state.posts];
      revertedPosts.insert(postIndex, post);
      state = state.copyWith(posts: revertedPosts);
      rethrow;
    }
  }
}

