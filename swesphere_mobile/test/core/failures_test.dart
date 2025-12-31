import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/core/error/failures.dart';

void main() {
  group('Failure classes', () {
    group('ServerFailure', () {
      test('creates with message', () {
        const failure = ServerFailure('Server error');
        expect(failure.message, 'Server error');
        expect(failure.statusCode, isNull);
      });

      test('creates with message and status code', () {
        const failure = ServerFailure('Not found', statusCode: 404);
        expect(failure.message, 'Not found');
        expect(failure.statusCode, 404);
      });

      test('equality works correctly', () {
        const failure1 = ServerFailure('Error', statusCode: 500);
        const failure2 = ServerFailure('Error', statusCode: 500);
        const failure3 = ServerFailure('Error', statusCode: 400);

        expect(failure1, equals(failure2));
        expect(failure1, isNot(equals(failure3)));
      });
    });

    group('NetworkFailure', () {
      test('has default message', () {
        const failure = NetworkFailure();
        expect(failure.message, 'No internet connection');
      });

      test('accepts custom message', () {
        const failure = NetworkFailure('Custom network error');
        expect(failure.message, 'Custom network error');
      });
    });

    group('CacheFailure', () {
      test('has default message', () {
        const failure = CacheFailure();
        expect(failure.message, 'Cache error');
      });
    });

    group('ValidationFailure', () {
      test('creates with message', () {
        const failure = ValidationFailure('Invalid input');
        expect(failure.message, 'Invalid input');
        expect(failure.fieldErrors, isNull);
      });

      test('creates with field errors', () {
        const failure = ValidationFailure(
          'Validation failed',
          fieldErrors: {'email': 'Invalid email'},
        );
        expect(failure.fieldErrors, {'email': 'Invalid email'});
      });
    });

    group('AuthFailure', () {
      test('has default message', () {
        const failure = AuthFailure();
        expect(failure.message, 'Authentication failed');
      });
    });

    group('NotFoundFailure', () {
      test('has default message', () {
        const failure = NotFoundFailure();
        expect(failure.message, 'Resource not found');
      });
    });

    group('PermissionFailure', () {
      test('has default message', () {
        const failure = PermissionFailure();
        expect(failure.message, 'Permission denied');
      });
    });
  });
}

