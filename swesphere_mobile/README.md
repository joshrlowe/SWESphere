# SWESphere Mobile

A Flutter mobile app for SWESphere - a Twitter-like social platform for developers.

## Architecture

This project follows **Clean Architecture** with the following layers:

```
lib/
├── main.dart                 # Entry point
├── app.dart                  # App widget with router
├── core/                     # Core utilities
│   ├── constants/            # App constants
│   ├── error/               # Failure classes
│   ├── network/             # API client & interceptors
│   ├── router/              # GoRouter configuration
│   └── theme/               # App theme & colors
├── features/                 # Feature modules
│   ├── auth/
│   │   ├── data/            # Data layer
│   │   │   ├── datasources/ # Remote/Local data sources
│   │   │   ├── models/      # JSON models
│   │   │   └── repositories/# Repository implementations
│   │   ├── domain/          # Business logic
│   │   │   ├── entities/    # Domain entities
│   │   │   ├── repositories/# Repository contracts
│   │   │   └── usecases/    # Use cases
│   │   └── presentation/    # UI layer
│   │       ├── providers/   # Riverpod providers
│   │       ├── pages/       # Screen widgets
│   │       └── widgets/     # Reusable widgets
│   ├── feed/
│   ├── profile/
│   └── notifications/
└── shared/                   # Shared widgets
    └── widgets/
```

## Tech Stack

- **State Management**: Riverpod 2.0 with code generation
- **Networking**: Dio with Retrofit
- **Navigation**: GoRouter
- **Local Storage**: Hive for caching, SecureStorage for tokens
- **Serialization**: json_serializable

## Getting Started

### Prerequisites

- Flutter SDK 3.0+
- Dart SDK 3.0+
- iOS: Xcode 14+
- Android: Android Studio with SDK 21+

### Setup

1. **Install dependencies**
   ```bash
   flutter pub get
   ```

2. **Generate code** (models, providers)
   ```bash
   flutter pub run build_runner build --delete-conflicting-outputs
   ```

3. **Run the app**
   ```bash
   # iOS
   flutter run -d ios
   
   # Android
   flutter run -d android
   ```

### Configuration

Update the API base URL in `lib/core/network/api_client.dart`:

```dart
abstract class ApiConfig {
  static const String baseUrl = 'http://localhost:8000';
  // Change to your production URL
}
```

## Features

- [x] Authentication (Login/Register)
- [x] Home Feed with infinite scroll
- [x] User Profiles
- [x] Notifications
- [x] Like/Unlike posts
- [x] Create posts
- [ ] Media attachments
- [ ] Direct Messages
- [ ] Search
- [ ] Settings

## Development

### Code Generation

After modifying models or providers, run:

```bash
# One-time build
flutter pub run build_runner build

# Watch mode (recommended)
flutter pub run build_runner watch
```

### Running Tests

```bash
# All tests
flutter test

# With coverage
flutter test --coverage
```

### Building for Release

```bash
# Android APK
flutter build apk --release

# Android App Bundle
flutter build appbundle --release

# iOS
flutter build ios --release
```

## Project Structure

| Directory | Description |
|-----------|-------------|
| `lib/core/` | Core infrastructure (API, theme, routing) |
| `lib/features/` | Feature modules following clean architecture |
| `lib/shared/` | Shared widgets used across features |
| `assets/` | Static assets (images, fonts, icons) |
| `test/` | Unit and widget tests |
| `integration_test/` | Integration tests |

## Contributing

1. Create a feature branch from `main`
2. Make your changes following the established patterns
3. Run tests and linting
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

