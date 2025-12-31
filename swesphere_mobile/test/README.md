# SWESphere Mobile Tests

This directory contains the comprehensive test suite for the SWESphere Flutter mobile application.

## Test Structure

```
test/
├── core/                           # Core module tests
│   ├── constants_test.dart
│   ├── failures_test.dart
│   ├── theme_test.dart
│   └── extensions/
│       └── context_extensions_test.dart
├── features/                       # Feature-specific tests
│   ├── auth/
│   │   ├── data/
│   │   │   └── models/
│   │   │       └── user_model_test.dart
│   │   ├── domain/
│   │   │   ├── repositories/
│   │   │   │   └── auth_repository_test.dart
│   │   │   └── usecases/
│   │   │       ├── login_test.dart
│   │   │       └── register_test.dart
│   │   └── user_entity_test.dart
│   ├── feed/
│   │   ├── data/
│   │   │   └── models/
│   │   │       └── post_model_test.dart
│   │   ├── domain/
│   │   │   ├── repositories/
│   │   │   │   └── feed_repository_test.dart
│   │   │   └── usecases/
│   │   │       ├── create_post_test.dart
│   │   │       └── like_post_test.dart
│   │   └── post_entity_test.dart
│   ├── notifications/
│   │   └── notification_entity_test.dart
│   └── profile/
│       └── domain/
│           ├── entities/
│           │   └── profile_test.dart
│           └── usecases/
│               ├── follow_user_test.dart
│               └── update_profile_test.dart
├── integration/                    # Integration tests
│   ├── auth_flow_test.dart
│   ├── feed_flow_test.dart
│   └── profile_flow_test.dart
└── shared/                         # Shared widgets tests
    └── widgets/
        ├── avatar_widget_test.dart
        ├── button_widget_test.dart
        ├── empty_state_test.dart
        ├── error_view_test.dart
        └── loading_indicator_test.dart
```

## Running Tests

### Run all tests
```bash
flutter test
```

### Run specific test file
```bash
flutter test test/features/auth/domain/usecases/login_test.dart
```

### Run tests with coverage
```bash
flutter test --coverage
```

### Run tests in a specific directory
```bash
flutter test test/features/auth/
```

### Run integration tests
```bash
flutter test test/integration/
```

### Run widget tests only
```bash
flutter test test/shared/widgets/
```

### Run tests with verbose output
```bash
flutter test --reporter expanded
```

## Test Categories

### Unit Tests
- **Domain Layer**: Entities, Use Cases, Repository contracts
- **Data Layer**: Models, JSON serialization, Repository implementations
- **Core**: Failures, Constants, Extensions

### Widget Tests
- **Shared Widgets**: Avatar, Button, Loading, Error, Empty states
- Tests widget rendering, interactions, and state management

### Integration Tests
- **Auth Flow**: Complete authentication workflow
- **Feed Flow**: Post creation, liking, pagination
- **Profile Flow**: Profile viewing, editing, following

## Test Coverage Goals

| Module | Target Coverage |
|--------|----------------|
| Domain Layer | 95% |
| Data Layer | 90% |
| Core | 90% |
| Shared Widgets | 85% |
| Presentation | 80% |

## Best Practices

1. **Follow AAA Pattern**: Arrange, Act, Assert
2. **Mock External Dependencies**: Use mock implementations for repositories
3. **Test Edge Cases**: Empty states, errors, boundary conditions
4. **Keep Tests Isolated**: Each test should be independent
5. **Use Descriptive Names**: Test names should describe expected behavior

## Adding New Tests

When adding new features, ensure you create tests for:

1. **Entity**: Test properties, equality, copyWith
2. **Model**: Test JSON serialization/deserialization
3. **Use Case**: Test business logic with mock repository
4. **Repository**: Test error handling and data transformation
5. **Widgets**: Test rendering and user interactions

