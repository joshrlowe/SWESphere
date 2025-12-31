import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/pages/login_page.dart';
import '../../features/auth/presentation/pages/register_page.dart';
import '../../features/auth/presentation/providers/auth_provider.dart';
import '../../features/feed/presentation/pages/feed_page.dart';
import '../../features/notifications/presentation/pages/notifications_page.dart';
import '../../features/profile/presentation/pages/profile_page.dart';
import '../../features/profile/presentation/pages/edit_profile_page.dart';
import '../theme/app_colors.dart';

/// Route paths
abstract class AppRoutes {
  // Auth routes
  static const String login = '/login';
  static const String register = '/register';
  static const String forgotPassword = '/forgot-password';
  
  // Main routes
  static const String home = '/';
  static const String feed = '/feed';
  static const String explore = '/explore';
  static const String notifications = '/notifications';
  static const String messages = '/messages';
  
  // Profile routes
  static const String profile = '/profile/:username';
  static const String editProfile = '/profile/edit';
  static const String followers = '/profile/:username/followers';
  static const String following = '/profile/:username/following';
  
  // Post routes
  static const String post = '/post/:id';
  static const String compose = '/compose';
  
  // Settings
  static const String settings = '/settings';
  
  /// Generate profile route with username
  static String profileRoute(String username) => '/profile/$username';
  
  /// Generate post route with id
  static String postRoute(int id) => '/post/$id';
}

/// Navigation key
final rootNavigatorKey = GlobalKey<NavigatorState>();
final shellNavigatorKey = GlobalKey<NavigatorState>();

/// GoRouter provider
final routerProvider = Provider<GoRouter>((ref) {
  final authState = ref.watch(authStateProvider);
  
  return GoRouter(
    navigatorKey: rootNavigatorKey,
    initialLocation: AppRoutes.feed,
    debugLogDiagnostics: true,
    
    // Redirect logic based on auth state
    redirect: (context, state) {
      final isLoggedIn = authState.maybeWhen(
        authenticated: (_) => true,
        orElse: () => false,
      );
      
      final isLoading = authState.maybeWhen(
        loading: () => true,
        orElse: () => false,
      );
      
      // Still loading, don't redirect
      if (isLoading) return null;
      
      final isAuthRoute = state.matchedLocation == AppRoutes.login ||
          state.matchedLocation == AppRoutes.register ||
          state.matchedLocation == AppRoutes.forgotPassword;
      
      // Not logged in and not on auth route -> go to login
      if (!isLoggedIn && !isAuthRoute) {
        return AppRoutes.login;
      }
      
      // Logged in and on auth route -> go to home
      if (isLoggedIn && isAuthRoute) {
        return AppRoutes.feed;
      }
      
      return null;
    },
    
    routes: [
      // =======================================================================
      // Auth Routes
      // =======================================================================
      GoRoute(
        path: AppRoutes.login,
        name: 'login',
        pageBuilder: (context, state) => CustomTransitionPage(
          key: state.pageKey,
          child: const LoginPage(),
          transitionsBuilder: (context, animation, secondaryAnimation, child) {
            return FadeTransition(opacity: animation, child: child);
          },
        ),
      ),
      GoRoute(
        path: AppRoutes.register,
        name: 'register',
        pageBuilder: (context, state) => CustomTransitionPage(
          key: state.pageKey,
          child: const RegisterPage(),
          transitionsBuilder: (context, animation, secondaryAnimation, child) {
            return SlideTransition(
              position: Tween<Offset>(
                begin: const Offset(1, 0),
                end: Offset.zero,
              ).animate(animation),
              child: child,
            );
          },
        ),
      ),
      
      // =======================================================================
      // Main Shell with Bottom Navigation
      // =======================================================================
      ShellRoute(
        navigatorKey: shellNavigatorKey,
        builder: (context, state, child) {
          return MainShell(child: child);
        },
        routes: [
          // Feed
          GoRoute(
            path: AppRoutes.feed,
            name: 'feed',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: FeedPage(),
            ),
          ),
          
          // Explore
          GoRoute(
            path: AppRoutes.explore,
            name: 'explore',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: Scaffold(
                body: Center(child: Text('Explore - Coming Soon')),
              ),
            ),
          ),
          
          // Notifications
          GoRoute(
            path: AppRoutes.notifications,
            name: 'notifications',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: NotificationsPage(),
            ),
          ),
          
          // Messages
          GoRoute(
            path: AppRoutes.messages,
            name: 'messages',
            pageBuilder: (context, state) => const NoTransitionPage(
              child: Scaffold(
                body: Center(child: Text('Messages - Coming Soon')),
              ),
            ),
          ),
        ],
      ),
      
      // =======================================================================
      // Profile Routes (outside shell)
      // =======================================================================
      GoRoute(
        path: AppRoutes.profile,
        name: 'profile',
        pageBuilder: (context, state) {
          final username = state.pathParameters['username']!;
          return MaterialPage(
            key: state.pageKey,
            child: ProfilePage(username: username),
          );
        },
      ),
      GoRoute(
        path: AppRoutes.editProfile,
        name: 'editProfile',
        pageBuilder: (context, state) => const MaterialPage(
          child: EditProfilePage(),
        ),
      ),
      
      // =======================================================================
      // Compose Route (modal)
      // =======================================================================
      GoRoute(
        path: AppRoutes.compose,
        name: 'compose',
        pageBuilder: (context, state) => CustomTransitionPage(
          key: state.pageKey,
          fullscreenDialog: true,
          child: const Scaffold(
            body: Center(child: Text('Compose - Coming Soon')),
          ),
          transitionsBuilder: (context, animation, secondaryAnimation, child) {
            return SlideTransition(
              position: Tween<Offset>(
                begin: const Offset(0, 1),
                end: Offset.zero,
              ).animate(CurvedAnimation(
                parent: animation,
                curve: Curves.easeOut,
              )),
              child: child,
            );
          },
        ),
      ),
    ],
    
    // Error page
    errorPageBuilder: (context, state) => MaterialPage(
      key: state.pageKey,
      child: Scaffold(
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(
                Icons.error_outline,
                size: 64,
                color: AppColors.error,
              ),
              const SizedBox(height: 16),
              Text(
                'Page not found',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(
                state.error?.message ?? 'Unknown error',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: () => context.go(AppRoutes.feed),
                child: const Text('Go Home'),
              ),
            ],
          ),
        ),
      ),
    ),
  );
});

/// Main Shell with Bottom Navigation
class MainShell extends StatelessWidget {
  final Widget child;

  const MainShell({super.key, required this.child});

  int _calculateSelectedIndex(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    if (location.startsWith(AppRoutes.feed)) return 0;
    if (location.startsWith(AppRoutes.explore)) return 1;
    if (location.startsWith(AppRoutes.notifications)) return 2;
    if (location.startsWith(AppRoutes.messages)) return 3;
    return 0;
  }

  @override
  Widget build(BuildContext context) {
    final selectedIndex = _calculateSelectedIndex(context);

    return Scaffold(
      body: child,
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          border: Border(
            top: BorderSide(color: AppColors.border, width: 0.5),
          ),
        ),
        child: BottomNavigationBar(
          currentIndex: selectedIndex,
          onTap: (index) {
            switch (index) {
              case 0:
                context.go(AppRoutes.feed);
                break;
              case 1:
                context.go(AppRoutes.explore);
                break;
              case 2:
                context.go(AppRoutes.notifications);
                break;
              case 3:
                context.go(AppRoutes.messages);
                break;
            }
          },
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.home_outlined),
              activeIcon: Icon(Icons.home),
              label: 'Home',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.search),
              activeIcon: Icon(Icons.search),
              label: 'Explore',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.notifications_outlined),
              activeIcon: Icon(Icons.notifications),
              label: 'Notifications',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.mail_outline),
              activeIcon: Icon(Icons.mail),
              label: 'Messages',
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.push(AppRoutes.compose),
        child: const Icon(Icons.add),
      ),
    );
  }
}

