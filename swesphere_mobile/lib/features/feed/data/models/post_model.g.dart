// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'post_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

PostModel _$PostModelFromJson(Map<String, dynamic> json) => PostModel(
      id: json['id'] as int,
      content: json['content'] as String,
      author: UserModel.fromJson(json['author'] as Map<String, dynamic>),
      likesCount: json['likes_count'] as int? ?? 0,
      repliesCount: json['replies_count'] as int? ?? 0,
      repostsCount: json['reposts_count'] as int? ?? 0,
      isLiked: json['is_liked'] as bool? ?? false,
      isReposted: json['is_reposted'] as bool? ?? false,
      isBookmarked: json['is_bookmarked'] as bool? ?? false,
      replyTo: json['reply_to'] == null
          ? null
          : PostModel.fromJson(json['reply_to'] as Map<String, dynamic>),
      repostOf: json['repost_of'] == null
          ? null
          : PostModel.fromJson(json['repost_of'] as Map<String, dynamic>),
      mediaUrls: (json['media_urls'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: json['updated_at'] == null
          ? null
          : DateTime.parse(json['updated_at'] as String),
    );

Map<String, dynamic> _$PostModelToJson(PostModel instance) => <String, dynamic>{
      'id': instance.id,
      'content': instance.content,
      'author': instance.author.toJson(),
      'likes_count': instance.likesCount,
      'replies_count': instance.repliesCount,
      'reposts_count': instance.repostsCount,
      'is_liked': instance.isLiked,
      'is_reposted': instance.isReposted,
      'is_bookmarked': instance.isBookmarked,
      'reply_to': instance.replyTo?.toJson(),
      'repost_of': instance.repostOf?.toJson(),
      'media_urls': instance.mediaUrls,
      'created_at': instance.createdAt.toIso8601String(),
      'updated_at': instance.updatedAt?.toIso8601String(),
    };

PaginatedPostsResponse _$PaginatedPostsResponseFromJson(
        Map<String, dynamic> json) =>
    PaginatedPostsResponse(
      items: (json['items'] as List<dynamic>)
          .map((e) => PostModel.fromJson(e as Map<String, dynamic>))
          .toList(),
      page: json['page'] as int,
      pages: json['pages'] as int,
      total: json['total'] as int,
      hasNext: json['has_next'] as bool,
      hasPrev: json['has_prev'] as bool,
    );

Map<String, dynamic> _$PaginatedPostsResponseToJson(
        PaginatedPostsResponse instance) =>
    <String, dynamic>{
      'items': instance.items.map((e) => e.toJson()).toList(),
      'page': instance.page,
      'pages': instance.pages,
      'total': instance.total,
      'has_next': instance.hasNext,
      'has_prev': instance.hasPrev,
    };

