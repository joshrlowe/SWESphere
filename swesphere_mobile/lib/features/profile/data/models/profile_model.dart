import 'package:json_annotation/json_annotation.dart';

import '../../../auth/data/models/user_model.dart';

part 'profile_model.g.dart';

/// Profile update request model
@JsonSerializable()
class UpdateProfileRequest {
  @JsonKey(name: 'display_name')
  final String? displayName;
  final String? bio;
  final String? location;
  final String? website;
  @JsonKey(name: 'avatar_url')
  final String? avatarUrl;
  @JsonKey(name: 'banner_url')
  final String? bannerUrl;

  const UpdateProfileRequest({
    this.displayName,
    this.bio,
    this.location,
    this.website,
    this.avatarUrl,
    this.bannerUrl,
  });

  factory UpdateProfileRequest.fromJson(Map<String, dynamic> json) =>
      _$UpdateProfileRequestFromJson(json);

  Map<String, dynamic> toJson() {
    final json = _$UpdateProfileRequestToJson(this);
    // Remove null values
    json.removeWhere((key, value) => value == null);
    return json;
  }
}

/// Paginated users response
@JsonSerializable()
class PaginatedUsersResponse {
  final List<UserModel> items;
  final int page;
  final int pages;
  final int total;
  @JsonKey(name: 'has_next')
  final bool hasNext;
  @JsonKey(name: 'has_prev')
  final bool hasPrev;

  const PaginatedUsersResponse({
    required this.items,
    required this.page,
    required this.pages,
    required this.total,
    required this.hasNext,
    required this.hasPrev,
  });

  factory PaginatedUsersResponse.fromJson(Map<String, dynamic> json) =>
      _$PaginatedUsersResponseFromJson(json);

  Map<String, dynamic> toJson() => _$PaginatedUsersResponseToJson(this);
}
