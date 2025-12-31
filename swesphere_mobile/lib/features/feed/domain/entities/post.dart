import 'package:equatable/equatable.dart';
import '../../../auth/domain/entities/user.dart';

/// Post entity
class Post extends Equatable {
  final int id;
  final String content;
  final User author;
  final int likesCount;
  final int repliesCount;
  final int repostsCount;
  final bool isLiked;
  final bool isReposted;
  final bool isBookmarked;
  final Post? replyTo;
  final Post? repostOf;
  final List<String>? mediaUrls;
  final DateTime createdAt;
  final DateTime? updatedAt;

  const Post({
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

  @override
  List<Object?> get props => [
        id,
        content,
        author,
        likesCount,
        repliesCount,
        repostsCount,
        isLiked,
        isReposted,
        isBookmarked,
        replyTo,
        repostOf,
        mediaUrls,
        createdAt,
        updatedAt,
      ];

  Post copyWith({
    int? id,
    String? content,
    User? author,
    int? likesCount,
    int? repliesCount,
    int? repostsCount,
    bool? isLiked,
    bool? isReposted,
    bool? isBookmarked,
    Post? replyTo,
    Post? repostOf,
    List<String>? mediaUrls,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return Post(
      id: id ?? this.id,
      content: content ?? this.content,
      author: author ?? this.author,
      likesCount: likesCount ?? this.likesCount,
      repliesCount: repliesCount ?? this.repliesCount,
      repostsCount: repostsCount ?? this.repostsCount,
      isLiked: isLiked ?? this.isLiked,
      isReposted: isReposted ?? this.isReposted,
      isBookmarked: isBookmarked ?? this.isBookmarked,
      replyTo: replyTo ?? this.replyTo,
      repostOf: repostOf ?? this.repostOf,
      mediaUrls: mediaUrls ?? this.mediaUrls,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}

