import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import 'button_widget.dart';

/// Error type for different error displays
enum ErrorType {
  generic,
  network,
  server,
  notFound,
  unauthorized,
  forbidden,
}

/// Error view widget
class ErrorView extends StatelessWidget {
  final String? title;
  final String? message;
  final ErrorType type;
  final VoidCallback? onRetry;
  final String? retryText;
  final VoidCallback? onSecondaryAction;
  final String? secondaryActionText;
  final bool showIcon;
  final double iconSize;

  const ErrorView({
    super.key,
    this.title,
    this.message,
    this.type = ErrorType.generic,
    this.onRetry,
    this.retryText,
    this.onSecondaryAction,
    this.secondaryActionText,
    this.showIcon = true,
    this.iconSize = 64,
  });

  /// Create from exception
  factory ErrorView.fromError(
    Object error, {
    VoidCallback? onRetry,
  }) {
    final errorString = error.toString().toLowerCase();

    if (errorString.contains('connection') ||
        errorString.contains('network') ||
        errorString.contains('socket')) {
      return ErrorView(
        type: ErrorType.network,
        onRetry: onRetry,
      );
    }

    if (errorString.contains('404') || errorString.contains('not found')) {
      return ErrorView(
        type: ErrorType.notFound,
        onRetry: onRetry,
      );
    }

    if (errorString.contains('401') || errorString.contains('unauthorized')) {
      return ErrorView(
        type: ErrorType.unauthorized,
        onRetry: onRetry,
      );
    }

    if (errorString.contains('403') || errorString.contains('forbidden')) {
      return ErrorView(
        type: ErrorType.forbidden,
        onRetry: onRetry,
      );
    }

    if (errorString.contains('500') || errorString.contains('server')) {
      return ErrorView(
        type: ErrorType.server,
        onRetry: onRetry,
      );
    }

    return ErrorView(
      message: error.toString(),
      onRetry: onRetry,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (showIcon) ...[
              Icon(
                _getIcon(),
                size: iconSize,
                color: _getIconColor(),
              ),
              const SizedBox(height: 24),
            ],
            Text(
              _getTitle(),
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              _getMessage(),
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSecondary,
                  ),
              textAlign: TextAlign.center,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: 24),
              AppButton(
                text: retryText ?? 'Try again',
                onPressed: onRetry,
                variant: ButtonVariant.primary,
              ),
            ],
            if (onSecondaryAction != null && secondaryActionText != null) ...[
              const SizedBox(height: 12),
              AppButton(
                text: secondaryActionText!,
                onPressed: onSecondaryAction,
                variant: ButtonVariant.text,
              ),
            ],
          ],
        ),
      ),
    );
  }

  IconData _getIcon() {
    switch (type) {
      case ErrorType.network:
        return Icons.wifi_off_rounded;
      case ErrorType.server:
        return Icons.cloud_off_rounded;
      case ErrorType.notFound:
        return Icons.search_off_rounded;
      case ErrorType.unauthorized:
        return Icons.lock_rounded;
      case ErrorType.forbidden:
        return Icons.block_rounded;
      case ErrorType.generic:
        return Icons.error_outline_rounded;
    }
  }

  Color _getIconColor() {
    switch (type) {
      case ErrorType.network:
        return AppColors.warning;
      case ErrorType.server:
        return AppColors.error;
      case ErrorType.notFound:
        return AppColors.textMuted;
      case ErrorType.unauthorized:
        return AppColors.warning;
      case ErrorType.forbidden:
        return AppColors.error;
      case ErrorType.generic:
        return AppColors.error;
    }
  }

  String _getTitle() {
    if (title != null) return title!;

    switch (type) {
      case ErrorType.network:
        return 'No connection';
      case ErrorType.server:
        return 'Server error';
      case ErrorType.notFound:
        return 'Not found';
      case ErrorType.unauthorized:
        return 'Session expired';
      case ErrorType.forbidden:
        return 'Access denied';
      case ErrorType.generic:
        return 'Something went wrong';
    }
  }

  String _getMessage() {
    if (message != null) return message!;

    switch (type) {
      case ErrorType.network:
        return 'Please check your internet connection and try again.';
      case ErrorType.server:
        return 'We\'re having trouble connecting to our servers. Please try again later.';
      case ErrorType.notFound:
        return 'The content you\'re looking for doesn\'t exist or has been removed.';
      case ErrorType.unauthorized:
        return 'Please sign in again to continue.';
      case ErrorType.forbidden:
        return 'You don\'t have permission to view this content.';
      case ErrorType.generic:
        return 'An unexpected error occurred. Please try again.';
    }
  }
}

/// Inline error message
class InlineError extends StatelessWidget {
  final String message;
  final VoidCallback? onDismiss;

  const InlineError({
    super.key,
    required this.message,
    this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.error.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.error.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.error_outline,
            color: AppColors.error,
            size: 20,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              message,
              style: const TextStyle(color: AppColors.error),
            ),
          ),
          if (onDismiss != null)
            GestureDetector(
              onTap: onDismiss,
              child: const Icon(
                Icons.close,
                color: AppColors.error,
                size: 18,
              ),
            ),
        ],
      ),
    );
  }
}

