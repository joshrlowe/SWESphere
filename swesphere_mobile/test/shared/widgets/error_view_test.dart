import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/shared/widgets/error_view.dart';

void main() {
  group('ErrorView', () {
    testWidgets('renders with default type', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ErrorView(),
          ),
        ),
      );

      expect(find.text('Something went wrong'), findsOneWidget);
      expect(find.byIcon(Icons.error_outline_rounded), findsOneWidget);
    });

    testWidgets('renders network error', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ErrorView(type: ErrorType.network),
          ),
        ),
      );

      expect(find.text('No connection'), findsOneWidget);
      expect(find.byIcon(Icons.wifi_off_rounded), findsOneWidget);
    });

    testWidgets('renders server error', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ErrorView(type: ErrorType.server),
          ),
        ),
      );

      expect(find.text('Server error'), findsOneWidget);
      expect(find.byIcon(Icons.cloud_off_rounded), findsOneWidget);
    });

    testWidgets('renders not found error', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ErrorView(type: ErrorType.notFound),
          ),
        ),
      );

      expect(find.text('Not found'), findsOneWidget);
    });

    testWidgets('renders unauthorized error', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ErrorView(type: ErrorType.unauthorized),
          ),
        ),
      );

      expect(find.text('Session expired'), findsOneWidget);
    });

    testWidgets('renders forbidden error', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ErrorView(type: ErrorType.forbidden),
          ),
        ),
      );

      expect(find.text('Access denied'), findsOneWidget);
    });

    testWidgets('uses custom title and message', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ErrorView(
              title: 'Custom Error',
              message: 'Something specific went wrong',
            ),
          ),
        ),
      );

      expect(find.text('Custom Error'), findsOneWidget);
      expect(find.text('Something specific went wrong'), findsOneWidget);
    });

    testWidgets('shows retry button when onRetry provided', (tester) async {
      bool retryCalled = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ErrorView(
              onRetry: () => retryCalled = true,
            ),
          ),
        ),
      );

      expect(find.text('Try again'), findsOneWidget);
      await tester.tap(find.text('Try again'));
      await tester.pumpAndSettle();
      expect(retryCalled, true);
    });

    testWidgets('uses custom retry text', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ErrorView(
              retryText: 'Reload',
              onRetry: () {},
            ),
          ),
        ),
      );

      expect(find.text('Reload'), findsOneWidget);
    });

    testWidgets('shows secondary action when provided', (tester) async {
      bool secondaryActionCalled = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ErrorView(
              secondaryActionText: 'Go Home',
              onSecondaryAction: () => secondaryActionCalled = true,
            ),
          ),
        ),
      );

      expect(find.text('Go Home'), findsOneWidget);
      await tester.tap(find.text('Go Home'));
      await tester.pumpAndSettle();
      expect(secondaryActionCalled, true);
    });

    testWidgets('hides icon when showIcon is false', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ErrorView(showIcon: false),
          ),
        ),
      );

      expect(find.byIcon(Icons.error_outline_rounded), findsNothing);
    });
  });

  group('ErrorView.fromError', () {
    testWidgets('creates network error from connection error', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ErrorView.fromError(Exception('Connection failed')),
          ),
        ),
      );

      expect(find.text('No connection'), findsOneWidget);
    });

    testWidgets('creates not found error from 404', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ErrorView.fromError(Exception('404 Not Found')),
          ),
        ),
      );

      expect(find.text('Not found'), findsOneWidget);
    });

    testWidgets('creates server error from 500', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ErrorView.fromError(Exception('500 Internal Server Error')),
          ),
        ),
      );

      expect(find.text('Server error'), findsOneWidget);
    });
  });

  group('InlineError', () {
    testWidgets('renders message', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: InlineError(message: 'Error occurred'),
          ),
        ),
      );

      expect(find.text('Error occurred'), findsOneWidget);
      expect(find.byIcon(Icons.error_outline), findsOneWidget);
    });

    testWidgets('shows close button when onDismiss provided', (tester) async {
      bool dismissed = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: InlineError(
              message: 'Error',
              onDismiss: () => dismissed = true,
            ),
          ),
        ),
      );

      expect(find.byIcon(Icons.close), findsOneWidget);
      await tester.tap(find.byIcon(Icons.close));
      expect(dismissed, true);
    });
  });
}

