import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../../../auth/domain/entities/user.dart';
import '../repositories/profile_repository.dart';

/// Get profile use case
class GetProfileUseCase {
  final ProfileRepository repository;

  GetProfileUseCase(this.repository);

  /// Execute - get user profile by username
  Future<Either<Failure, User>> call(String username) async {
    return repository.getProfile(username);
  }
}

