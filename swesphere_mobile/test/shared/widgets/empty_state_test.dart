import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/shared/widgets/empty_state.dart';

void main() {
  group('EmptyState', () {
    testWidgets('renders with default type', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EmptyState(),
          ),
        ),
      );

      expect(find.text('Nothing here'), findsOneWidget);
      expect(find.byIcon(Icons.inbox_outlined), findsOneWidget);
    });

    testWidgets('renders posts empty state', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EmptyState(type: EmptyStateType.posts),
          ),
        ),
      );

      expect(find.text('No posts yet'), findsOneWidget);
      expect(find.byIcon(Icons.article_outlined), findsOneWidget);
    });

    testWidgets('renders notifications empty state', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EmptyState(type: EmptyStateType.notifications),
          ),
        ),
      );

      expect(find.text('No notifications'), findsOneWidget);
      expect(find.byIcon(Icons.notifications_none_outlined), findsOneWidget);
    });

    testWidgets('renders search empty state', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EmptyState(type: EmptyStateType.search),
          ),
        ),
      );

      expect(find.text('No results found'), findsOneWidget);
    });

    testWidgets('uses custom title and message', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EmptyState(
              title: 'Custom Title',
              message: 'Custom message',
            ),
          ),
        ),
      );

      expect(find.text('Custom Title'), findsOneWidget);
      expect(find.text('Custom message'), findsOneWidget);
    });

    testWidgets('shows action button when provided', (tester) async {
      bool actionCalled = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: EmptyState(
              actionText: 'Take Action',
              onAction: () => actionCalled = true,
            ),
          ),
        ),
      );

      expect(find.text('Take Action'), findsOneWidget);
      await tester.tap(find.text('Take Action'));
      expect(actionCalled, true);
    });

    testWidgets('uses custom icon', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EmptyState(icon: Icons.star),
          ),
        ),
      );

      expect(find.byIcon(Icons.star), findsOneWidget);
    });
  });

  group('SearchEmptyState', () {
    testWidgets('shows query in title', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SearchEmptyState(query: 'flutter'),
          ),
        ),
      );

      expect(find.text('No results for "flutter"'), findsOneWidget);
    });

    testWidgets('shows custom suggestion', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SearchEmptyState(
              query: 'test',
              suggestion: 'Try a different keyword',
            ),
          ),
        ),
      );

      expect(find.text('Try a different keyword'), findsOneWidget);
    });
  });

  group('FeedEmptyState', () {
    testWidgets('renders welcome message', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: FeedEmptyState(),
          ),
        ),
      );

      expect(find.text('Welcome to SWESphere!'), findsOneWidget);
    });

    testWidgets('shows explore button', (tester) async {
      bool exploreCalled = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: FeedEmptyState(
              onExplore: () => exploreCalled = true,
            ),
          ),
        ),
      );

      await tester.tap(find.text('Explore'));
      expect(exploreCalled, true);
    });
  });

  group('ProfilePostsEmptyState', () {
    testWidgets('shows create post for own profile', (tester) async {
      bool createPostCalled = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ProfilePostsEmptyState(
              isOwnProfile: true,
              onCreatePost: () => createPostCalled = true,
            ),
          ),
        ),
      );

      expect(find.text('Share your thoughts'), findsOneWidget);
      await tester.tap(find.text('Create post'));
      expect(createPostCalled, true);
    });

    testWidgets('shows different message for other profiles', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ProfilePostsEmptyState(isOwnProfile: false),
          ),
        ),
      );

      expect(find.text('This user hasn\'t posted anything yet.'), findsOneWidget);
    });
  });
}

