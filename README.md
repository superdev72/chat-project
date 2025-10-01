# Real-Time Chat Application

A real-time chat application built with Python, Django, Redis, and WebSockets. This application allows users to send and receive messages in real-time with proper authentication, email verification, and message throttling.

## Features

- **User Authentication**: Registration, login, and email verification
- **Real-time Messaging**: WebSocket-based real-time chat functionality
- **Redis Integration**: Fast message storage and retrieval using Redis
- **PostgreSQL Database**: User management and conversation metadata
- **Email Verification**: MailHog integration for email verification
- **API Throttling**: Rate limiting for message sending (10 messages per minute)
- **Comprehensive Logging**: All API calls are logged with detailed information
- **Docker Support**: Complete containerization with Docker Compose
- **Testing**: Unit tests and integration tests included
- **CI/CD**: GitHub Actions workflow for automated testing

## Technology Stack

- **Backend**: Python 3.11, Django 4.2.7
- **Database**: PostgreSQL 15
- **Cache/Message Store**: Redis 7
- **Real-time Communication**: Django Channels with WebSockets
- **Email Service**: MailHog (for development)
- **Containerization**: Docker & Docker Compose
- **API**: Django REST Framework
- **Authentication**: Token-based authentication

## Project Structure

```
chat-project/
├── apps/
│   ├── accounts/          # User authentication and management
│   └── chat/              # Chat functionality and WebSocket consumers
├── chat_project/          # Django project settings
├── templates/             # Email templates
├── tests/                 # Test files
├── .github/workflows/     # GitHub Actions CI/CD
├── docker-compose.yml     # Docker services configuration
├── Dockerfile            # Docker image configuration
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Git

## Quick Start with Docker

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd chat-project
   ```

2. **Create environment file**

   ```bash
   cp env.example .env
   ```

3. **Start the services**

   ```bash
   docker-compose up --build
   ```

4. **Run migrations**

   ```bash
   docker-compose exec web python manage.py migrate
   ```

5. **Create superuser (optional)**

   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

6. **Access the application**
   - API: http://localhost:8000/api/
   - Admin: http://localhost:8000/admin/
   - MailHog UI: http://localhost:8025/

## Manual Setup (Without Docker)

1. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up PostgreSQL**

   - Install PostgreSQL
   - Create database: `createdb chatdb`
   - Update DATABASE_URL in .env file

4. **Set up Redis**

   - Install Redis
   - Start Redis server: `redis-server`

5. **Set up MailHog**

   ```bash
   # Download and run MailHog
   # Or use: go install github.com/mailhog/MailHog@latest
   mailhog
   ```

6. **Run migrations**

   ```bash
   python manage.py migrate
   ```

7. **Start the development server**
   ```bash
   python manage.py runserver
   ```

## API Endpoints

### Authentication

- `POST /api/auth/register/` - User registration
- `POST /api/auth/login/` - User login
- `GET /api/auth/profile/` - Get user profile
- `POST /api/auth/verify-email/<token>/` - Email verification
- `POST /api/auth/resend-verification/` - Resend verification email

### Chat

- `GET /api/chat/rooms/` - List user's chat rooms
- `POST /api/chat/rooms/` - Create new chat room
- `GET /api/chat/rooms/<id>/` - Get chat room details
- `PUT /api/chat/rooms/<id>/` - Update chat room
- `DELETE /api/chat/rooms/<id>/` - Delete chat room
- `GET /api/chat/rooms/<id>/messages/` - Get messages
- `POST /api/chat/rooms/<id>/send/` - Send message
- `POST /api/chat/rooms/<id>/participants/` - Add participant
- `DELETE /api/chat/rooms/<id>/participants/<user_id>/` - Remove participant
- `DELETE /api/chat/messages/<message_id>/` - Delete message

### WebSocket

- `ws://localhost:8000/ws/chat/<chat_room_id>/` - WebSocket connection for real-time chat

## API Usage Examples

### User Registration

```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "username": "johndoe",
    "password": "securepassword123",
    "password_confirm": "securepassword123"
  }'
```

### User Login

```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "securepassword123"
  }'
```

### Create Chat Room

```bash
curl -X POST http://localhost:8000/api/chat/rooms/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <your-token>" \
  -d '{
    "name": "My Chat Room",
    "participant_emails": ["user2@example.com"]
  }'
```

### Send Message

```bash
curl -X POST http://localhost:8000/api/chat/rooms/<room-id>/send/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token <your-token>" \
  -d '{
    "content": "Hello, World!"
  }'
```

## WebSocket Usage

Connect to WebSocket for real-time messaging:

```javascript
const chatSocket = new WebSocket("ws://localhost:8000/ws/chat/<room-id>/");

chatSocket.onmessage = function (e) {
  const data = JSON.parse(e.data);
  if (data.type === "chat_message") {
    // Handle incoming message
    console.log("New message:", data.content);
  }
};

// Send message
chatSocket.send(
  JSON.stringify({
    type: "chat_message",
    content: "Hello from WebSocket!",
  })
);

// Send typing indicator
chatSocket.send(
  JSON.stringify({
    type: "typing",
  })
);
```

## Testing

### Run Tests

```bash
# With Docker
docker-compose exec web python manage.py test

# Without Docker
python manage.py test
```

### Test Coverage

```bash
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://chatuser:chatpass@localhost:5433/chatdb
REDIS_URL=redis://localhost:6379/0

# Email settings for MailHog
EMAIL_HOST=localhost
EMAIL_PORT=1025
EMAIL_USE_TLS=False
EMAIL_USE_SSL=False

# Site settings
SITE_URL=http://localhost:8000
```

### Database Configuration

The application uses PostgreSQL with the following default settings:

- Host: localhost
- Port: 5433 (to avoid conflicts with existing PostgreSQL)
- Database: chatdb
- User: chatuser
- Password: chatpass

### Redis Configuration

Redis is used for:

- Real-time message storage
- WebSocket channel layers
- Caching

Default Redis configuration:

- Host: localhost
- Port: 6380 (to avoid conflicts with existing Redis)
- Database: 0

## API Throttling

The application implements rate limiting:

- **Anonymous users**: 100 requests per hour
- **Authenticated users**: 1000 requests per hour
- **Message sending**: 10 messages per minute per user

## Logging

All API calls are logged with the following information:

- Request method and path
- User information
- IP address
- User agent
- Response status and duration
- Timestamp

Logs are stored in:

- `logs/django.log` - General application logs
- `logs/api.log` - API-specific logs

## Security Features

- Email verification for user registration
- Token-based authentication
- CORS protection
- SQL injection protection
- XSS protection
- CSRF protection
- Rate limiting
- Input validation

## Deployment

### Production Deployment

1. **Set production environment variables**

   ```env
   DEBUG=False
   SECRET_KEY=your-production-secret-key
   DATABASE_URL=postgresql://user:pass@host:port/db
   REDIS_URL=redis://host:port/0
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   ```

2. **Use production email service**

   ```env
   EMAIL_HOST=smtp.your-provider.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@domain.com
   EMAIL_HOST_PASSWORD=your-email-password
   ```

3. **Deploy with Docker**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

### Cloud Deployment Options

- **Heroku**: Use Heroku Postgres and Redis add-ons
- **AWS**: Use RDS for PostgreSQL and ElastiCache for Redis
- **Google Cloud**: Use Cloud SQL and Memorystore
- **Azure**: Use Azure Database for PostgreSQL and Azure Cache for Redis

## Monitoring

The application includes comprehensive logging and monitoring:

- API request/response logging
- Error tracking
- Performance monitoring
- User activity logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions, please open an issue in the repository.

## Changelog

### Version 1.0.0

- Initial release
- User authentication with email verification
- Real-time chat functionality
- Redis integration
- Docker support
- Comprehensive testing
- CI/CD pipeline
