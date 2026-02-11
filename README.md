# SDCP Social Post Generator

AI-powered social media post generator for San Diego Custom Painting.

## Features

- **Photo Upload**: Upload project photos through the web dashboard
- **AI Caption Generation**: Claude AI analyzes photos and generates platform-specific captions
- **Approval Workflow**: Email notifications with approve/edit/reject actions
- **Scheduled Publishing**: Posts scheduled for optimal times via APScheduler
- **Multi-Platform**: Publishes to both Instagram and Facebook

## Tech Stack

- **Backend**: FastAPI + Python 3.11+
- **Database**: PostgreSQL with SQLAlchemy
- **AI**: Anthropic Claude API (vision)
- **Email**: Resend
- **Publishing**: Meta Graph API (Instagram + Facebook)
- **Hosting**: Railway

## Setup

1. Copy `.env.example` to `.env` and fill in your API keys
2. Run database migrations: `alembic upgrade head`
3. Start the server: `uvicorn main:app --reload`

## Environment Variables

See `.env.example` for all required configuration.
