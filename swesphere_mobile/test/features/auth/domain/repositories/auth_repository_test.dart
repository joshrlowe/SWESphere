import 'package:flutter_test/flutter_test.dart';
import 'package:swesphere_mobile/features/auth/domain/repositories/auth_repository.dart';

void main() {
  group('LoginCredentials', () {
    test('creates with required fields', () {
      const credentials = LoginCredentials(
        email: 'test@example.com',
        password: 'password123',
      );

      expect(credentials.email, 'test@example.com');
      expect(credentials.password, 'password123');
    });
  });

  group('RegisterData', () {
    test('creates with required fields', () {
      const data = RegisterData(
        username: 'testuser',
        email: 'test@example.com',
        password: 'password123',
      );

      expect(data.username, 'testuser');
      expect(data.email, 'test@example.com');
      expect(data.password, 'password123');
    });
  });

  group('AuthTokens', () {
    test('creates with tokens', () {
      const tokens = AuthTokens(
        accessToken: 'access_token_here',
        refreshToken: 'refresh_token_here',
      );

      expect(tokens.accessToken, 'access_token_here');
      expect(tokens.refreshToken, 'refresh_token_here');
    });
  });
}

