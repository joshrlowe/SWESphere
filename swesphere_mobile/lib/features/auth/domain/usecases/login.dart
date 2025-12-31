import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../entities/user.dart';
import '../repositories/auth_repository.dart';

/// Login use case
class LoginUseCase {
  final AuthRepository repository;

  LoginUseCase(this.repository);

  /// Execute login with email and password
  Future<Either<Failure, User>> call(LoginParams params) async {
    final result = await repository.login(
      LoginCredentials(
        email: params.email,
        password: params.password,
      ),
    );

    return result.map((tuple) => tuple.$1);
  }
}

/// Login parameters
class LoginParams {
  final String email;
  final String password;

  const LoginParams({
    required this.email,
    required this.password,
  });
}

