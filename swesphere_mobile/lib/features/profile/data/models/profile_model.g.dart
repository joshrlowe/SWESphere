// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'profile_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

UpdateProfileRequest _$UpdateProfileRequestFromJson(
        Map<String, dynamic> json) =>
    UpdateProfileRequest(
      displayName: json['display_name'] as String?,
      bio: json['bio'] as String?,
      location: json['location'] as String?,
      website: json['website'] as String?,
      avatarUrl: json['avatar_url'] as String?,
      bannerUrl: json['banner_url'] as String?,
    );

Map<String, dynamic> _$UpdateProfileRequestToJson(
    UpdateProfileRequest instance) {
  final val = <String, dynamic>{};

  void writeNotNull(String key, dynamic value) {
    if (value != null) {
      val[key] = value;
    }
  }

  writeNotNull('display_name', instance.displayName);
  writeNotNull('bio', instance.bio);
  writeNotNull('location', instance.location);
  writeNotNull('website', instance.website);
  writeNotNull('avatar_url', instance.avatarUrl);
  writeNotNull('banner_url', instance.bannerUrl);
  return val;
}

PaginatedUsersResponse _$PaginatedUsersResponseFromJson(
        Map<String, dynamic> json) =>
    PaginatedUsersResponse(
      items: (json['items'] as List<dynamic>)
          .map((e) => UserModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      page: json['page'] as int,
      pages: json['pages'] as int,
      total: json['total'] as int,
      hasNext: json['has_next'] as bool,
      hasPrev: json['has_prev'] as bool,
    );

Map<String, dynamic> _$PaginatedUsersResponseToJson(
        PaginatedUsersResponse instance) =>
    <String, dynamic>{
      'items': instance.items.map((e) => e.toJson()).toList(),
      'page': instance.page,
      'pages': instance.pages,
      'total': instance.total,
      'has_next': instance.hasNext,
      'has_prev': instance.hasPrev,
    };

