import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/theme/app_colors.dart';
import '../../../auth/presentation/providers/auth_provider.dart';
import '../../domain/usecases/create_post.dart';

/// Composer mode
enum ComposerMode {
  newPost,
  reply,
}

/// Post composer widget
class PostComposer extends ConsumerStatefulWidget {
  final ComposerMode mode;
  final int? replyToPostId;
  final VoidCallback? onPostCreated;
  final VoidCallback? onCancel;

  const PostComposer({
    super.key,
    this.mode = ComposerMode.newPost,
    this.replyToPostId,
    this.onPostCreated,
    this.onCancel,
  });

  @override
  ConsumerState<PostComposer> createState() => _PostComposerState();
}

class _PostComposerState extends ConsumerState<PostComposer> {
  final _controller = TextEditingController();
  final _focusNode = FocusNode();
  
  bool _isPosting = false;

  @override
  void initState() {
    super.initState();
    _controller.addListener(() => setState(() {}));
    // Auto focus on open
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focusNode.requestFocus();
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  int get _remainingChars => CreatePostParams.maxContentLength - _controller.text.length;
  
  bool get _canPost => 
      _controller.text.trim().isNotEmpty && 
      _remainingChars >= 0 && 
      !_isPosting;

  Color get _counterColor {
    if (_remainingChars < 0) return AppColors.error;
    if (_remainingChars < 20) return AppColors.warning;
    return AppColors.textSecondary;
  }

  Future<void> _handlePost() async {
    if (!_canPost) return;

    setState(() => _isPosting = true);

    try {
      // Post will be handled by the parent - just validate here
      final params = CreatePostParams(
        content: _controller.text,
        replyToId: widget.replyToPostId,
      );

      final error = params.validate();
      if (error != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(error)),
        );
        return;
      }

      widget.onPostCreated?.call();
    } finally {
      if (mounted) {
        setState(() => _isPosting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final currentUser = ref.watch(currentUserProvider);

    return Container(
      color: AppColors.background,
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: const BoxDecoration(
                border: Border(
                  bottom: BorderSide(color: AppColors.border),
                ),
              ),
              child: Row(
                children: [
                  TextButton(
                    onPressed: widget.onCancel,
                    child: const Text('Cancel'),
                  ),
                  const Spacer(),
                  ElevatedButton(
                    onPressed: _canPost ? _handlePost : null,
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 20,
                        vertical: 8,
                      ),
                    ),
                    child: _isPosting
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : Text(widget.mode == ComposerMode.reply ? 'Reply' : 'Post'),
                  ),
                ],
              ),
            ),

            // Composer area
            Expanded(
              child: SingleChildScrollView(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Avatar
                      CircleAvatar(
                        radius: 20,
                        backgroundColor: AppColors.surface,
                        backgroundImage: currentUser?.avatarUrl != null
                            ? NetworkImage(currentUser!.avatarUrl!)
                            : null,
                        child: currentUser?.avatarUrl == null
                            ? Text(
                                currentUser?.name[0].toUpperCase() ?? 'U',
                                style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                ),
                              )
                            : null,
                      ),
                      const SizedBox(width: 12),

                      // Text field
                      Expanded(
                        child: TextField(
                          controller: _controller,
                          focusNode: _focusNode,
                          maxLines: null,
                          minLines: 5,
                          maxLength: CreatePostParams.maxContentLength + 20,
                          buildCounter: (context, {
                            required currentLength,
                            required isFocused,
                            maxLength,
                          }) => null,
                          decoration: InputDecoration(
                            hintText: widget.mode == ComposerMode.reply
                                ? 'Post your reply'
                                : "What's happening?",
                            border: InputBorder.none,
                            enabledBorder: InputBorder.none,
                            focusedBorder: InputBorder.none,
                            fillColor: Colors.transparent,
                            filled: true,
                            contentPadding: EdgeInsets.zero,
                          ),
                          style: Theme.of(context).textTheme.bodyLarge,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),

            // Footer with actions
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: const BoxDecoration(
                border: Border(
                  top: BorderSide(color: AppColors.border),
                ),
              ),
              child: Row(
                children: [
                  // Media buttons
                  IconButton(
                    icon: const Icon(Icons.image_outlined),
                    color: AppColors.primary,
                    onPressed: () {
                      // TODO: Add image picker
                    },
                  ),
                  IconButton(
                    icon: const Icon(Icons.gif_box_outlined),
                    color: AppColors.primary,
                    onPressed: () {
                      // TODO: Add GIF picker
                    },
                  ),
                  IconButton(
                    icon: const Icon(Icons.poll_outlined),
                    color: AppColors.primary,
                    onPressed: () {
                      // TODO: Add poll creation
                    },
                  ),
                  IconButton(
                    icon: const Icon(Icons.location_on_outlined),
                    color: AppColors.primary,
                    onPressed: () {
                      // TODO: Add location
                    },
                  ),
                  
                  const Spacer(),

                  // Character counter
                  if (_controller.text.isNotEmpty) ...[
                    // Progress indicator
                    SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(
                        value: _controller.text.length / CreatePostParams.maxContentLength,
                        strokeWidth: 2,
                        backgroundColor: AppColors.border,
                        valueColor: AlwaysStoppedAnimation(_counterColor),
                      ),
                    ),
                    const SizedBox(width: 8),
                    if (_remainingChars <= 20)
                      Text(
                        '$_remainingChars',
                        style: TextStyle(
                          color: _counterColor,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Full-screen compose page
class ComposePage extends StatelessWidget {
  final ComposerMode mode;
  final int? replyToPostId;

  const ComposePage({
    super.key,
    this.mode = ComposerMode.newPost,
    this.replyToPostId,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: PostComposer(
        mode: mode,
        replyToPostId: replyToPostId,
        onCancel: () => Navigator.of(context).pop(),
        onPostCreated: () {
          Navigator.of(context).pop(true);
        },
      ),
    );
  }
}

