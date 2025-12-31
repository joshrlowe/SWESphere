import 'package:dartz/dartz.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/core/error/failures.dart';
import 'package:swesphere_mobile/features/auth/domain/entities/user.dart';
import 'package:swesphere_mobile/features/auth/domain/repositories/auth_repository.dart';
import 'package:swesphere_mobile/features/auth/domain/usecases/login.dart';

// Mock repository
class MockAuthRepository implements AuthRepository {
  bool shouldSucceed = true;
  User? userToReturn;
  Failure? failureToReturn;

  @override
  Future<Either<Failure, (User, AuthTokens)>> login(LoginCredentials credentials) async {
    if (shouldSucceed && userToReturn != null) {
      return Right((
        userToReturn!,
        const AuthTokens(accessToken: 'token', refreshToken: 'refresh'),
      ));
    }
    return Left(failureToReturn ?? const AuthFailure());
  }

  @override
  Future<Either<Failure, User>> register(RegisterData data) async {
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
  late LoginUseCase useCase;
  late MockAuthRepository repository;

  setUp(() {
    repository = MockAuthRepository();
    useCase = LoginUseCase(repository);
  });

  final testUser = User(
    id: 1,
    username: 'testuser',
    email: 'test@example.com',
    createdAt: DateTime(2024, 1, 1),
  );

  group('LoginUseCase', () {
    test('returns User on successful login', () async {
      repository.shouldSucceed = true;
      repository.userToReturn = testUser;

      final result = await useCase(const LoginParams(
        email: 'test@example.com',
        password: 'password123',
      ));

      expect(result.isRight(), true);
      result.fold(
        (failure) => fail('Expected success'),
        (user) {
          expect(user.email, 'test@example.com');
          expect(user.username, 'testuser');
        },
      );
    });

    test('returns AuthFailure on failed login', () async {
      repository.shouldSucceed = false;
      repository.failureToReturn = const AuthFailure('Invalid credentials');

      final result = await useCase(const LoginParams(
        email: 'test@example.com',
        password: 'wrongpassword',
      ));

      expect(result.isLeft(), true);
      result.fold(
        (failure) {
          expect(failure, isA<AuthFailure>());
          expect(failure.message, 'Invalid credentials');
        },
        (user) => fail('Expected failure'),
      );
    });
  });

  group('LoginParams', () {
    test('creates with required fields', () {
      const params = LoginParams(
        email: 'test@example.com',
        password: 'password123',
      );

      expect(params.email, 'test@example.com');
      expect(params.password, 'password123');
    });
  });
}

