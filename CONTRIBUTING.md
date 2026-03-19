# Contributing to NasFusion

Thank you for your interest in contributing to NasFusion! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Git
- Docker & Docker Compose (optional, for testing)

### Development Setup

1. **Fork and clone the repository**

```bash
git clone https://github.com/YOUR_USERNAME/NasFusion.git
cd NasFusion
```

2. **Set up the backend**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
python -m app.main
```

3. **Set up the frontend**

```bash
cd frontend
npm install
npm run dev
```

## How to Contribute

### Reporting Bugs

- Check if the bug has already been reported in [Issues](../../issues)
- Use the bug report template
- Include:
  - Steps to reproduce
  - Expected behavior
  - Actual behavior
  - Environment details (OS, Python version, etc.)

### Suggesting Features

- Check if the feature has already been suggested
- Open a new issue with the feature request template
- Describe:
  - The problem you're trying to solve
  - Your proposed solution
  - Any alternatives you've considered

### Submitting Pull Requests

1. **Create a branch**

```bash
git checkout -b feature/your-feature-name
# or: git checkout -b fix/your-bug-fix
```

2. **Make your changes**

Follow the coding standards below.

3. **Test your changes**

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm run test
```

4. **Commit your changes**

Use clear, descriptive commit messages in Chinese or English:

```bash
git commit -m "feat: 添加新功能描述"
git commit -m "fix: 修复某个问题"
git commit -m "docs: 更新文档"
```

5. **Push and create a Pull Request**

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Coding Standards

### Backend (Python)

- Follow PEP 8 style guide
- Use type hints
- Use async/await for I/O operations
- Use constants instead of magic strings (see `app/constants/`)
- Document functions with docstrings

```python
# Good example
from app.constants import MEDIA_TYPE_MOVIE

async def get_media_by_type(db: AsyncSession, media_type: str) -> list[Media]:
    """
    Get media items by type.

    Args:
        db: Database session
        media_type: Type of media (movie/tv)

    Returns:
        List of media items
    """
    result = await db.execute(
        select(Media).where(Media.type == media_type)
    )
    return result.scalars().all()
```

### Frontend (Vue/TypeScript)

- Use TypeScript
- Follow Vue 3 Composition API patterns
- Use Element Plus components
- Keep components small and focused

### Database

- Use Alembic for migrations
- Always review auto-generated migrations before committing
- Test migrations on a fresh database

```bash
# Generate migration
alembic revision --autogenerate -m "Description of changes"

# Review the generated file!
# Apply migration
alembic upgrade head
```

## Project Structure

```
backend/
├── app/
│   ├── adapters/     # External system adapters
│   ├── api/v1/       # API routes
│   ├── constants/    # Constants (avoid magic strings)
│   ├── core/         # Core configuration
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Business logic
│   └── tasks/        # Background tasks
└── docs/             # Documentation

frontend/
├── src/
│   ├── api/          # API client
│   ├── components/   # Vue components
│   ├── stores/       # Pinia stores
│   └── views/        # Page views
```

## Documentation

- Update documentation when making changes
- Add docstrings to new functions
- Update README if adding new features

## Questions?

Feel free to open an issue for any questions or discussions.

Thank you for contributing!
