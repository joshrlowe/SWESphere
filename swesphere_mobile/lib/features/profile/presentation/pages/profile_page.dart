import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/router/app_router.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../shared/widgets/empty_state.dart';
import '../../../../shared/widgets/error_view.dart';
import '../../../../shared/widgets/loading_indicator.dart';
import '../../../../shared/widgets/post_card.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../providers/profile_provider.dart';
import '../widgets/profile_header.dart';

class ProfilePage extends ConsumerStatefulWidget {
  final String username;

  const ProfilePage({super.key, required this.username});

  @override
  ConsumerState<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends ConsumerState<ProfilePage>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    _tabController.addListener(_onTabChanged);
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _tabController.removeListener(_onTabChanged);
    _tabController.dispose();
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onTabChanged() {
    if (!_tabController.indexIsChanging) {
      final tab = ProfileTab.values[_tabController.index];
      ref.read(profileProvider(widget.username).notifier).changeTab(tab);
    }
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      ref.read(profileProvider(widget.username).notifier).loadMore();
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(profileProvider(widget.username));
    final currentUser = ref.watch(currentUserProvider);
    final isOwnProfile = currentUser?.username == widget.username;

    return Scaffold(
      body: RefreshIndicator(
        onRefresh: () =>
            ref.read(profileProvider(widget.username).notifier).refresh(),
        color: AppColors.primary,
        backgroundColor: AppColors.surface,
        child: _buildBody(state, isOwnProfile),
      ),
    );
  }

  Widget _buildBody(ProfileState state, bool isOwnProfile) {
    if (state.isLoading && state.user == null) {
      return const CenteredLoading();
    }

    if (state.error != null && state.user == null) {
      return ErrorView(
        type: ErrorType.generic,
        message: state.error,
        onRetry: () =>
            ref.read(profileProvider(widget.username).notifier).loadProfile(),
      );
    }

    if (state.user == null) {
      return const ErrorView(
        type: ErrorType.notFound,
        title: 'User not found',
      );
    }

    return CustomScrollView(
      controller: _scrollController,
      physics: const AlwaysScrollableScrollPhysics(),
      slivers: [
        // App Bar
        SliverAppBar(
          pinned: true,
          expandedHeight: 0,
          leading: IconButton(
            icon: Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.5),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.arrow_back, color: Colors.white, size: 18),
            ),
            onPressed: () => context.pop(),
          ),
          backgroundColor: AppColors.background,
        ),

        // Profile header
        SliverToBoxAdapter(
          child: ProfileHeader(
            user: state.user!,
            isOwnProfile: isOwnProfile,
            onEditProfile: () => context.push(AppRoutes.editProfile),
            onFollow: () => ref
                .read(profileProvider(widget.username).notifier)
                .toggleFollow(),
            onFollowersPressed: () {
              // TODO: Navigate to followers
            },
            onFollowingPressed: () {
              // TODO: Navigate to following
            },
          ),
        ),

        // Tabs
        SliverPersistentHeader(
          pinned: true,
          delegate: _TabBarDelegate(
            TabBar(
              controller: _tabController,
              tabs: const [
                Tab(text: 'Posts'),
                Tab(text: 'Replies'),
                Tab(text: 'Media'),
                Tab(text: 'Likes'),
              ],
              labelColor: AppColors.textPrimary,
              unselectedLabelColor: AppColors.textSecondary,
              indicatorColor: AppColors.primary,
              indicatorSize: TabBarIndicatorSize.label,
            ),
          ),
        ),

        // Posts content
        if (state.isLoadingPosts)
          const SliverFillRemaining(
            child: CenteredLoading(),
          )
        else if (state.posts.isEmpty)
          SliverFillRemaining(
            child: ProfilePostsEmptyState(
              isOwnProfile: isOwnProfile,
              onCreatePost: () => context.push(AppRoutes.compose),
            ),
          )
        else
          SliverList(
            delegate: SliverChildBuilderDelegate(
              (context, index) {
                if (index == state.posts.length) {
                  return state.isLoadingMore
                      ? const Padding(
                          padding: EdgeInsets.all(24),
                          child: CenteredLoading(),
                        )
                      : const SizedBox.shrink();
                }

                final post = state.posts[index];
                return Column(
                  children: [
                    PostCard(
                      post: post,
                      onLike: () {
                        // TODO: Implement like
                      },
                    ),
                    const Divider(height: 1),
                  ],
                );
              },
              childCount: state.posts.length + (state.hasMorePosts ? 1 : 0),
            ),
          ),
      ],
    );
  }
}

class _TabBarDelegate extends SliverPersistentHeaderDelegate {
  final TabBar tabBar;

  _TabBarDelegate(this.tabBar);

  @override
  Widget build(context, shrinkOffset, overlapsContent) {
    return Container(
      color: AppColors.background,
      child: tabBar,
    );
  }

  @override
  double get maxExtent => tabBar.preferredSize.height;

  @override
  double get minExtent => tabBar.preferredSize.height;

  @override
  bool shouldRebuild(covariant SliverPersistentHeaderDelegate oldDelegate) =>
      false;
}
