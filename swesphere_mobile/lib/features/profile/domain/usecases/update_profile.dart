import 'package:dartz/dartz.dart';

import '../../../../core/error/failures.dart';
import '../../../auth/domain/entities/user.dart';
import '../repositories/profile_repository.dart';

/// Update profile use case
class UpdateProfileUseCase {
  final ProfileRepository repository;

  UpdateProfileUseCase(this.repository);

  /// Execute - update user profile
  Future<Either<Failure, User>> call(UpdateProfileParams params) async {
    // Validate params
    final error = params.validate();
    if (error != null) {
      return Left(ValidationFailure(error));
    }

    return repository.updateProfile(UpdateProfileData(
      displayName: params.displayName,
      bio: params.bio,
      location: params.location,
      website: params.website,
      avatarUrl: params.avatarUrl,
      bannerUrl: params.bannerUrl,
    ));
  }
}

/// Update profile parameters
class UpdateProfileParams {
  final String? displayName;
  final String? bio;
  final String? location;
  final String? website;
  final String? avatarUrl;
  final String? bannerUrl;

  static const int maxDisplayNameLength = 50;
  static const int maxBioLength = 160;
  static const int maxLocationLength = 30;
  static const int maxWebsiteLength = 100;

  const UpdateProfileParams({
    this.displayName,
    this.bio,
    this.location,
    this.website,
    this.avatarUrl,
    this.bannerUrl,
  });

  /// Validate parameters
  String? validate() {
    if (displayName != null && displayName!.length > maxDisplayNameLength) {
      return 'Display name must be less than $maxDisplayNameLength characters';
    }
    if (bio != null && bio!.length > maxBioLength) {
      return 'Bio must be less than $maxBioLength characters';
    }
    if (location != null && location!.length > maxLocationLength) {
      return 'Location must be less than $maxLocationLength characters';
    }
    if (website != null && website!.length > maxWebsiteLength) {
      return 'Website must be less than $maxWebsiteLength characters';
    }
    if (website != null && website!.isNotEmpty) {
      // Basic URL validation
      final urlRegex = RegExp(
        r'^(https?:\/\/)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$',
      );
      if (!urlRegex.hasMatch(website!)) {
        return 'Please enter a valid website URL';
      }
    }
    return null;
  }
}

