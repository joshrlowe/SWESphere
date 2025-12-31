import 'package:equatable/equatable.dart';
import '../../../auth/domain/entities/user.dart';

/// Notification types
enum NotificationType {
  like,
  reply,
  follow,
  mention,
  repost,
}

/// Notification entity
class AppNotification extends Equatable {
  final int id;
  final NotificationType type;
  final User actor;
  final int? postId;
  final String? postContent;
  final bool isRead;
  final DateTime createdAt;

  const AppNotification({
    required this.id,
    required this.type,
    required this.actor,
    this.postId,
    this.postContent,
    this.isRead = false,
    required this.createdAt,
  });

  @override
  List<Object?> get props => [
        id,
        type,
        actor,
        postId,
        postContent,
        isRead,
        createdAt,
      ];

  AppNotification copyWith({
    int? id,
    NotificationType? type,
    User? actor,
    int? postId,
    String? postContent,
    bool? isRead,
    DateTime? createdAt,
  }) {
    return AppNotification(
      id: id ?? this.id,
      type: type ?? this.type,
      actor: actor ?? this.actor,
      postId: postId ?? this.postId,
      postContent: postContent ?? this.postContent,
      isRead: isRead ?? this.isRead,
      createdAt: createdAt ?? this.createdAt,
    );
  }

  /// Get notification message
  String get message {
    switch (type) {
      case NotificationType.like:
        return 'liked your post';
      case NotificationType.reply:
        return 'replied to your post';
      case NotificationType.follow:
        return 'followed you';
      case NotificationType.mention:
        return 'mentioned you';
      case NotificationType.repost:
        return 'reposted your post';
    }
  }
}

