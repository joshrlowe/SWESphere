import 'package:equatable/equatable.dart';

import '../../../auth/domain/entities/user.dart';

/// Notification types
enum NotificationType {
  like,
  reply,
  repost,
  follow,
  mention,
  quote,
}

/// Notification entity
class AppNotification extends Equatable {
  final int id;
  final NotificationType type;
  final User fromUser;
  final int? postId;
  final String? postContent;
  final bool isRead;
  final DateTime createdAt;

  const AppNotification({
    required this.id,
    required this.type,
    required this.fromUser,
    this.postId,
    this.postContent,
    this.isRead = false,
    required this.createdAt,
  });

  @override
  List<Object?> get props => [
        id,
        type,
        fromUser,
        postId,
        postContent,
        isRead,
        createdAt,
      ];

  AppNotification copyWith({
    int? id,
    NotificationType? type,
    User? fromUser,
    int? postId,
    String? postContent,
    bool? isRead,
    DateTime? createdAt,
  }) {
    return AppNotification(
      id: id ?? this.id,
      type: type ?? this.type,
      fromUser: fromUser ?? this.fromUser,
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
        return '${fromUser.name} liked your post';
      case NotificationType.reply:
        return '${fromUser.name} replied to your post';
      case NotificationType.repost:
        return '${fromUser.name} reposted your post';
      case NotificationType.follow:
        return '${fromUser.name} followed you';
      case NotificationType.mention:
        return '${fromUser.name} mentioned you';
      case NotificationType.quote:
        return '${fromUser.name} quoted your post';
    }
  }
}
