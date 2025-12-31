import 'package:json_annotation/json_annotation.dart';
import '../../../auth/data/models/user_model.dart';
import '../../domain/entities/post.dart';

part 'post_model.g.dart';

/// Post model for JSON serialization
@JsonSerializable()
class PostModel {
  final int id;
  final String content;
  final UserModel author;
  @JsonKey(name: 'likes_count')
  final int likesCount;
  @JsonKey(name: 'replies_count')
  final int repliesCount;
  @JsonKey(name: 'reposts_count')
  final int repostsCount;
  @JsonKey(name: 'is_liked')
  final bool isLiked;
  @JsonKey(name: 'is_reposted')
  final bool isReposted;
  @JsonKey(name: 'is_bookmarked')
  final bool isBookmarked;
  @JsonKey(name: 'reply_to')
  final PostModel? replyTo;
  @JsonKey(name: 'repost_of')
  final PostModel? repostOf;
  @JsonKey(name: 'media_urls')
  final List<String>? mediaUrls;
  @JsonKey(name: 'created_at')
  final DateTime createdAt;
  @JsonKey(name: 'updated_at')
  final DateTime? updatedAt;

  const PostModel({
    required this.id,
    required this.content,
    required this.author,
    this.likesCount = 0,
    this.repliesCount = 0,
    this.repostsCount = 0,
    this.isLiked = false,
    this.isReposted = false,
    this.isBookmarked = false,
    this.replyTo,
    this.repostOf,
    this.mediaUrls,
    required this.createdAt,
    this.updatedAt,
  });

  factory PostModel.fromJson(Map<String, dynamic> json) =>
      _$PostModelFromJson(json);

  Map<String, dynamic> toJson() => _$PostModelToJson(this);

  /// Convert to domain entity
  Post toEntity() {
    return Post(
      id: id,
      content: content,
      author: author.toEntity(),
      likesCount: likesCount,
      repliesCount: repliesCount,
      repostsCount: repostsCount,
      isLiked: isLiked,
      isReposted: isReposted,
      isBookmarked: isBookmarked,
      replyTo: replyTo?.toEntity(),
      repostOf: repostOf?.toEntity(),
      mediaUrls: mediaUrls,
      createdAt: createdAt,
      updatedAt: updatedAt,
    );
  }
}

/// Paginated posts response
@JsonSerializable()
class PaginatedPostsResponse {
  final List<PostModel> items;
  final int page;
  final int pages;
  @JsonKey(name: 'total')
  final int total;
  @JsonKey(name: 'has_next')
  final bool hasNext;
  @JsonKey(name: 'has_prev')
  final bool hasPrev;

  const PaginatedPostsResponse({
    required this.items,
    required this.page,
    required this.pages,
    required this.total,
    required this.hasNext,
    required this.hasPrev,
  });

  factory PaginatedPostsResponse.fromJson(Map<String, dynamic> json) =>
      _$PaginatedPostsResponseFromJson(json);

  Map<String, dynamic> toJson() => _$PaginatedPostsResponseToJson(this);
}

