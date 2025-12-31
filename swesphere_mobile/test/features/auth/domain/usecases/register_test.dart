import 'package:dartz/dartz.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/core/error/failures.dart';
import 'package:swesphere_mobile/features/auth/domain/entities/user.dart';
import 'package:swesphere_mobile/features/auth/domain/repositories/auth_repository.dart';
import 'package:swesphere_mobile/features/auth/domain/usecases/register.dart';

// Mock repository
class MockAuthRepository implements AuthRepository {
  bool shouldSucceed = true;
  User? userToReturn;
  Failure? failureToReturn;

  @override
  Future<Either<Failure, User>> register(RegisterData data) async {
    if (shouldSucceed && userToReturn != null) {
      return Right(userToReturn!);
    }
    return Left(failureToReturn ?? const ValidationFailure('Registration failed'));
  }

  @override
  Future<Either<Failure, (User, AuthTokens)>> login(LoginCredentials credentials) async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, void>> logout() async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, User>> getCurrentUser() async {
    throw UnimplementedError();
  }

  @override
  Future<Either<Failure, AuthTokens>> refreshToken(String refreshToken) async {
    throw UnimplementedError();
  }

  @override
  Future<bool> isAuthenticated() async => false;

  @override
  Future<String?> getAccessToken() async => null;

  @override
  Future<void> clearTokens() async {}
}

void main() {
  late RegisterUseCase useCase;
  late MockAuthRepository repository;

  setUp(() {
    repository = MockAuthRepository();
    useCase = RegisterUseCase(repository);
  });

  final testUser = User(
    id: 1,
    username: 'newuser',
    email: 'newuser@example.com',
    createdAt: DateTime(2024, 1, 1),
  );

  group('RegisterUseCase', () {
    test('returns User on successful registration', () async {
      repository.shouldSucceed = true;
      repository.userToReturn = testUser;

      final result = await useCase(const RegisterParams(
        username: 'newuser',
        email: 'newuser@example.com',
        password: 'password123',
      ));

      expect(result.isRight(), true);
      result.fold(
        (failure) => fail('Expected success'),
        (user) {
          expect(user.username, 'newuser');
          expect(user.email, 'newuser@example.com');
        },
      );
    });

    test('returns failure on registration error', () async {
      repository.shouldSucceed = false;
      repository.failureToReturn = const ValidationFailure('Email already exists');

      final result = await useCase(const RegisterParams(
        username: 'existinguser',
        email: 'existing@example.com',
        password: 'password123',
      ));

      expect(result.isLeft(), true);
      result.fold(
        (failure) {
          expect(failure, isA<ValidationFailure>());
        },
        (user) => fail('Expected failure'),
      );
    });
  });

  group('RegisterParams', () {
    group('validateUsername', () {
      test('returns null for valid username', () {
        const params = RegisterParams(
          username: 'valid_user123',
          email: 'test@example.com',
          password: 'password123',
        );
        expect(params.validateUsername(), isNull);
      });

      test('returns error for empty username', () {
        const params = RegisterParams(
          username: '',
          email: 'test@example.com',
          password: 'password123',
        );
        expect(params.validateUsername(), 'Username is required');
      });

      test('returns error for short username', () {
        const params = RegisterParams(
          username: 'ab',
          email: 'test@example.com',
          password: 'password123',
        );
        expect(params.validateUsername(), 'Username must be at least 3 characters');
      });

      test('returns error for long username', () {
        const params = RegisterParams(
          username: 'a' * 21,
          email: 'test@example.com',
          password: 'password123',
        );
        expect(params.validateUsername(), 'Username must be less than 20 characters');
      });

      test('returns error for invalid characters', () {
        const params = RegisterParams(
          username: 'user@name!',
          email: 'test@example.com',
          password: 'password123',
        );
        expect(
          params.validateUsername(),
          'Username can only contain letters, numbers, and underscores',
        );
      });
    });

    group('validateEmail', () {
      test('returns null for valid email', () {
        const params = RegisterParams(
          username: 'testuser',
          email: 'test@example.com',
          password: 'password123',
        );
        expect(params.validateEmail(), isNull);
      });

      test('returns error for empty email', () {
        const params = RegisterParams(
          username: 'testuser',
          email: '',
          password: 'password123',
        );
        expect(params.validateEmail(), 'Email is required');
      });

      test('returns error for invalid email', () {
        const params = RegisterParams(
          username: 'testuser',
          email: 'invalid-email',
          password: 'password123',
        );
        expect(params.validateEmail(), 'Enter a valid email address');
      });
    });

    group('validatePassword', () {
      test('returns null for valid password', () {
        const params = RegisterParams(
          username: 'testuser',
          email: 'test@example.com',
          password: 'password123',
        );
        expect(params.validatePassword(), isNull);
      });

      test('returns error for empty password', () {
        const params = RegisterParams(
          username: 'testuser',
          email: 'test@example.com',
          password: '',
        );
        expect(params.validatePassword(), 'Password is required');
      });

      test('returns error for short password', () {
        const params = RegisterParams(
          username: 'testuser',
          email: 'test@example.com',
          password: 'short',
        );
        expect(params.validatePassword(), 'Password must be at least 8 characters');
      });
    });
  });
}

