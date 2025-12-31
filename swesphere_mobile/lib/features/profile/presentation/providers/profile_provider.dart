import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/network/api_client.dart';
import '../../../auth/domain/entities/user.dart';
import '../../../auth/data/models/user_model.dart';
import '../../../feed/domain/entities/post.dart';
import '../../../feed/data/models/post_model.dart';

/// Profile state
class ProfileState {
  final User? user;
  final List<Post> posts;
  final bool isLoading;
  final bool isLoadingPosts;
  final bool isLoadingMore;
  final bool hasMorePosts;
  final int currentPage;
  final String? error;
  final ProfileTab currentTab;

  const ProfileState({
    this.user,
    this.posts = const [],
    this.isLoading = false,
    this.isLoadingPosts = false,
    this.isLoadingMore = false,
    this.hasMorePosts = true,
    this.currentPage = 1,
    this.error,
    this.currentTab = ProfileTab.posts,
  });

  ProfileState copyWith({
    User? user,
    List<Post>? posts,
    bool? isLoading,
    bool? isLoadingPosts,
    bool? isLoadingMore,
    bool? hasMorePosts,
    int? currentPage,
    String? error,
    ProfileTab? currentTab,
  }) {
    return ProfileState(
      user: user ?? this.user,
      posts: posts ?? this.posts,
      isLoading: isLoading ?? this.isLoading,
      isLoadingPosts: isLoadingPosts ?? this.isLoadingPosts,
      isLoadingMore: isLoadingMore ?? this.isLoadingMore,
      hasMorePosts: hasMorePosts ?? this.hasMorePosts,
      currentPage: currentPage ?? this.currentPage,
      error: error,
      currentTab: currentTab ?? this.currentTab,
    );
  }
}

/// Profile tabs
enum ProfileTab {
  posts,
  replies,
  media,
  likes,
}

/// Profile provider family - keyed by username
final profileProvider = StateNotifierProvider.family<ProfileNotifier, ProfileState, String>(
  (ref, username) {
    return ProfileNotifier(
      username: username,
      apiClient: ref.watch(apiClientProvider),
    );
  },
);

/// Profile notifier
class ProfileNotifier extends StateNotifier<ProfileState> {
  final String username;
  final ApiClient _apiClient;

  ProfileNotifier({
    required this.username,
    required ApiClient apiClient,
  })  : _apiClient = apiClient,
        super(const ProfileState()) {
    loadProfile();
  }

  /// Load profile data
  Future<void> loadProfile() async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final response = await _apiClient.get('/users/$username');
      final user = UserModel.fromJson(
        response.data as Map<String, dynamic>,
      ).toEntity();

      state = state.copyWith(
        user: user,
        isLoading: false,
      );

      // Load posts for the current tab
      await loadTabPosts();
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Change current tab
  Future<void> changeTab(ProfileTab tab) async {
    if (state.currentTab == tab) return;

    state = state.copyWith(
      currentTab: tab,
      posts: [],
      currentPage: 1,
      hasMorePosts: true,
    );

    await loadTabPosts();
  }

  /// Load posts for current tab
  Future<void> loadTabPosts() async {
    state = state.copyWith(isLoadingPosts: true, error: null);

    try {
      final endpoint = _getTabEndpoint();
      final response = await _apiClient.get(
        endpoint,
        queryParameters: {'page': 1, 'size': 20},
      );

      final data = PaginatedPostsResponse.fromJson(
        response.data as Map<String, dynamic>,
      );

      state = state.copyWith(
        posts: data.items.map((p) => p.toEntity()).toList(),
        isLoadingPosts: false,
        hasMorePosts: data.hasNext,
        currentPage: data.page,
      );
    } catch (e) {
      state = state.copyWith(
        isLoadingPosts: false,
        error: e.toString(),
      );
    }
  }

  /// Load more posts
  Future<void> loadMore() async {
    if (state.isLoadingMore || !state.hasMorePosts) return;

    state = state.copyWith(isLoadingMore: true);

    try {
      final nextPage = state.currentPage + 1;
      final endpoint = _getTabEndpoint();
      final response = await _apiClient.get(
        endpoint,
        queryParameters: {'page': nextPage, 'size': 20},
      );

      final data = PaginatedPostsResponse.fromJson(
        response.data as Map<String, dynamic>,
      );

      state = state.copyWith(
        posts: [...state.posts, ...data.items.map((p) => p.toEntity())],
        isLoadingMore: false,
        hasMorePosts: data.hasNext,
        currentPage: data.page,
      );
    } catch (e) {
      state = state.copyWith(
        isLoadingMore: false,
        error: e.toString(),
      );
    }
  }

  /// Refresh profile
  Future<void> refresh() async {
    state = state.copyWith(currentPage: 1, hasMorePosts: true);
    await loadProfile();
  }

  /// Toggle follow
  Future<void> toggleFollow() async {
    final user = state.user;
    if (user == null) return;

    // Optimistic update
    final isFollowing = user.isFollowing;
    state = state.copyWith(
      user: user.copyWith(
        isFollowing: !isFollowing,
        followersCount: isFollowing
            ? user.followersCount - 1
            : user.followersCount + 1,
      ),
    );

    try {
      if (isFollowing) {
        await _apiClient.delete('/users/$username/follow');
      } else {
        await _apiClient.post('/users/$username/follow');
      }
    } catch (e) {
      // Revert on error
      state = state.copyWith(user: user);
    }
  }

  String _getTabEndpoint() {
    switch (state.currentTab) {
      case ProfileTab.posts:
        return '/users/$username/posts';
      case ProfileTab.replies:
        return '/users/$username/replies';
      case ProfileTab.media:
        return '/users/$username/media';
      case ProfileTab.likes:
        return '/users/$username/likes';
    }
  }
}

