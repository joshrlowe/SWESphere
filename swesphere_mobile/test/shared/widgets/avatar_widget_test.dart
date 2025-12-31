import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/shared/widgets/avatar_widget.dart';

void main() {
  group('AvatarWidget', () {
    testWidgets('renders with default size', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: AvatarWidget(name: 'John'),
          ),
        ),
      );

      expect(find.byType(AvatarWidget), findsOneWidget);
    });

    testWidgets('shows initial when no image', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: AvatarWidget(name: 'John Doe'),
          ),
        ),
      );

      expect(find.text('J'), findsOneWidget);
    });

    testWidgets('shows uppercase initial', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: AvatarWidget(name: 'john'),
          ),
        ),
      );

      expect(find.text('J'), findsOneWidget);
    });

    testWidgets('shows ? when name is null', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: AvatarWidget(),
          ),
        ),
      );

      expect(find.text('?'), findsOneWidget);
    });

    testWidgets('calls onTap when tapped', (tester) async {
      bool tapped = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: AvatarWidget(
              name: 'John',
              onTap: () => tapped = true,
            ),
          ),
        ),
      );

      await tester.tap(find.byType(AvatarWidget));
      expect(tapped, true);
    });

    testWidgets('respects size parameter', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: AvatarWidget(
              name: 'John',
              size: 80,
            ),
          ),
        ),
      );

      final container = tester.widget<Container>(find.byType(Container).first);
      expect(container.constraints?.maxWidth, 80);
      expect(container.constraints?.maxHeight, 80);
    });

    testWidgets('shows border when showBorder is true', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: AvatarWidget(
              name: 'John',
              showBorder: true,
              borderWidth: 3,
            ),
          ),
        ),
      );

      final container = tester.widget<Container>(find.byType(Container).first);
      final decoration = container.decoration as BoxDecoration;
      expect(decoration.border, isNotNull);
    });
  });

  group('AvatarGroup', () {
    testWidgets('renders multiple avatars', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: AvatarGroup(
              avatars: [
                AvatarData(name: 'Alice'),
                AvatarData(name: 'Bob'),
                AvatarData(name: 'Charlie'),
              ],
            ),
          ),
        ),
      );

      expect(find.byType(AvatarWidget), findsNWidgets(3));
    });

    testWidgets('limits visible avatars to maxVisible', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: AvatarGroup(
              avatars: [
                AvatarData(name: 'Alice'),
                AvatarData(name: 'Bob'),
                AvatarData(name: 'Charlie'),
                AvatarData(name: 'David'),
                AvatarData(name: 'Eve'),
              ],
              maxVisible: 3,
            ),
          ),
        ),
      );

      expect(find.byType(AvatarWidget), findsNWidgets(3));
      expect(find.text('+2'), findsOneWidget);
    });

    testWidgets('does not show overflow when all visible', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: AvatarGroup(
              avatars: [
                AvatarData(name: 'Alice'),
                AvatarData(name: 'Bob'),
              ],
              maxVisible: 3,
            ),
          ),
        ),
      );

      expect(find.text('+'), findsNothing);
    });
  });

  group('AvatarData', () {
    test('creates with imageUrl', () {
      const data = AvatarData(imageUrl: 'https://example.com/avatar.jpg');
      expect(data.imageUrl, 'https://example.com/avatar.jpg');
    });

    test('creates with name', () {
      const data = AvatarData(name: 'John');
      expect(data.name, 'John');
    });

    test('allows both imageUrl and name', () {
      const data = AvatarData(
        imageUrl: 'https://example.com/avatar.jpg',
        name: 'John',
      );
      expect(data.imageUrl, isNotNull);
      expect(data.name, 'John');
    });
  });
}

