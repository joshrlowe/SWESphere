# SWESphere

A Twitter-like social media platform built with Flask, featuring user authentication, posts, following system, real-time notifications, and multi-language support.

## Features

- **User Authentication**: Secure registration, login, password reset with email verification
- **Posts**: Create, view, and interact with posts (140 character limit)
- **Social**: Follow/unfollow users, personalized feed
- **Likes & Comments**: React to posts and engage in discussions
- **User Profiles**: Customizable profiles with avatar uploads
- **Search**: Find users and posts
- **Real-time Notifications**: WebSocket-based instant notifications
- **Internationalization**: Support for 12+ languages
- **REST API**: Full API access for third-party integrations
- **Security**: Rate limiting, account lockout, CSP headers, CSRF protection

## Tech Stack

- **Backend**: Python 3.11+ with Flask
- **Database**: SQLAlchemy with PostgreSQL (SQLite for development)
- **Authentication**: Flask-Login with JWT tokens
- **Real-time**: Flask-SocketIO with WebSockets
- **API**: Flask-RESTX with OpenAPI/Swagger docs
- **Frontend**: Bootstrap 5, Jinja2 templates
- **i18n**: Flask-Babel

## Quick Start

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- PostgreSQL (optional, SQLite works for development)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/swesphere/swesphere.git
   cd swesphere
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize the database**
   ```bash
   flask db upgrade
   ```

6. **Run the application**
   ```bash
   flask run
   ```

   The application will be available at `http://localhost:5000`

### Environment Variables

Create a `.env` file with the following variables:

```env
# Required
SECRET_KEY=your-secret-key-here

# Database (optional, defaults to SQLite)
DATABASE_URL=postgresql://user:password@localhost/swesphere

# Email (required for password reset)
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password
ADMINS=admin@example.com

# Redis (required for rate limiting and real-time features)
REDIS_URL=redis://localhost:6379/0
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_models.py
```

### Code Quality

```bash
# Install pre-commit hooks
pre-commit install

# Run linter
ruff check .

# Run formatter
ruff format .

# Type checking
mypy app
```

### Database Migrations

```bash
# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback last migration
flask db downgrade
```

### Translation Management

```bash
# Extract translatable strings
flask translate update

# Compile translations
flask translate compile

# Add a new language
flask translate init LANG_CODE
```

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f web

# Stop all services
docker-compose down
```

### Using Docker Only

```bash
# Build the image
docker build -t swesphere .

# Run the container
docker run -d -p 5000:5000 \
  -e SECRET_KEY=your-secret-key \
  -e DATABASE_URL=your-database-url \
  swesphere
```

## API Documentation

When running the application, API documentation is available at:
- Swagger UI: `http://localhost:5000/api/docs`
- OpenAPI Spec: `http://localhost:5000/api/swagger.json`

### API Authentication

The API uses JWT Bearer tokens. To authenticate:

1. Obtain a token via `POST /api/v1/auth/login`
2. Include the token in requests: `Authorization: Bearer <token>`

## Project Structure

```
swesphere/
├── app/
│   ├── __init__.py          # App factory and extensions
│   ├── models.py             # SQLAlchemy models
│   ├── routes.py             # Web routes
│   ├── forms.py              # WTForms definitions
│   ├── email.py              # Email utilities
│   ├── errors.py             # Error handlers
│   ├── cli.py                # CLI commands
│   ├── api/                  # REST API blueprint
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── users.py
│   │   └── posts.py
│   ├── static/               # Static files
│   │   ├── images/
│   │   └── uploads/
│   ├── templates/            # Jinja2 templates
│   └── translations/         # i18n files
├── migrations/               # Database migrations
├── tests/                    # Test suite
├── config.py                 # Configuration
├── swesphere.py              # Entry point
├── requirements.txt          # Dependencies
├── Dockerfile                # Docker image
├── docker-compose.yml        # Docker Compose config
└── README.md
```

## Security

SWESphere implements multiple security measures:

- **HTTPS Enforcement**: HSTS headers with 6-month duration
- **Content Security Policy**: Strict CSP with nonce-based inline scripts
- **CSRF Protection**: All forms protected via Flask-WTF
- **Secure Cookies**: HttpOnly, Secure, SameSite=Lax
- **Password Hashing**: PBKDF2 via Werkzeug
- **Rate Limiting**: Protection against brute-force attacks
- **Account Lockout**: Progressive lockout after failed attempts
- **Input Validation**: Server-side validation on all inputs
- **SQL Injection Prevention**: Parameterized queries via SQLAlchemy

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure:
- All tests pass (`pytest`)
- Code is formatted (`ruff format .`)
- No linting errors (`ruff check .`)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Flask](https://flask.palletsprojects.com/) - The web framework
- [Bootstrap](https://getbootstrap.com/) - Frontend framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
