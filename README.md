# 🛠️ Maintenance Executions API

> Enterprise-grade Form Management System for Maintenance Operations

## 📋 Overview

The Maintenance Executions API is a robust Flask-based system designed to streamline maintenance operations through dynamic form management, role-based access control, and comprehensive data collection capabilities.

### 🎯 Key Features

- **👥 Advanced User Management**
  - JWT-based authentication
  - Role-based access control (RBAC)
  - Multi-environment support
  - Granular permissions system

- **📝 Dynamic Form Management**
  - Customizable form creation
  - Multiple question types
  - File attachments support
  - Public/private form visibility

- **🏗️ Technical Highlights**
  - RESTful API architecture
  - PostgreSQL database
  - Modular Flask application
  - Environment-based data isolation

## 🏛️ Architecture

### System Components

```
maintenance-api/
├── 📁 app/
│   ├── models/          # Database entities
│   ├── controllers/     # Business logic
│   ├── services/        # Core services
│   ├── views/          # API endpoints
│   └── utils/          # Helper functions
├── 📁 management/       # CLI tools
└── 📄 config.py        # Configuration
```

### 🗄️ Core Modules

#### 1. User Management
- Authentication & Authorization
- Role-based permissions
- Environment segregation
- User profiles

#### 2. Form Management
- Dynamic form creation
- Question type handling
- Answer collection
- File attachments

#### 3. Data Collection
- Form submissions
- File uploads
- Answer validation
- Data export

## 🔐 Security Features

- **JWT Authentication**
  - Token-based access control
  - Refresh token mechanism
  - Secure password hashing

- **Role-Based Access**
  - Hierarchical permissions
  - Environment isolation
  - Action-based authorization

## 💾 Database Structure

### Core Entities

```mermaid
erDiagram
    User ||--o{ Form : creates
    Form ||--o{ Question : contains
    Question ||--o{ Answer : has
    Form ||--o{ Submission : receives
    User ||--o{ Submission : submits
    Environment ||--o{ User : contains
```

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Virtual environment

### Installation

```bash
# Clone repository
git clone https://github.com/RobertoAnguloDeveloper/maintenance_executions_api.git

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Unix
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Initialize database
flask database setup
```

## 🔧 Configuration

### Environment Variables

```plaintext
DATABASE_URL=postgresql://user:pass@localhost/dbname
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret
```

### Database Configuration

```bash
# Initialize database
flask database init

# Create test data
flask database testdata
```

## 📚 API Documentation

### Authentication

```http
POST /api/users/login
Content-Type: application/json

{
    "username": "user@example.com",
    "password": "secure_password"
}
```

### Form Management

```http
# Create Form
POST /api/forms
Authorization: Bearer <token>

# Submit Form
POST /api/forms/{form_id}/submit
Authorization: Bearer <token>
```

## 🔑 Role Hierarchy

1. **Admin**
   - Full system access
   - User management
   - System configuration

2. **Site Manager**
   - Environment management
   - User management within environment
   - Form management

3. **Supervisor**
   - Form creation
   - Submission review
   - Report generation

4. **Technician**
   - Form submission
   - View assigned forms
   - File attachments

## 📈 Features & Capabilities

### Form Types

- Maintenance Checklists
- Equipment Inspections
- Safety Assessments
- Incident Reports
- Work Orders

### Question Types

- Single Text
- Multiple Choice
- Checkboxes
- Date/Time
- File Upload
- Signature

### Data Export

- CSV Export
- PDF Reports
- Excel Sheets
- JSON Data

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- 📧 Email: roberto.angulo.developer@gmail.com
- 📝 Issues: GitHub Issues

---

Built with ❤️ by Your Organization