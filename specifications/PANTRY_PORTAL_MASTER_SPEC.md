# PANTRY PORTAL MASTER SPECIFICATION

## Product Name

Pantry Portal

## Tagline

Know What's In Your Home.

---

# MISSION

Create a complete SaaS platform that allows homeowners and families to maintain a real-time inventory of food, household products, consumables, appliances, furniture, valuables, electronics, tools, and other belongings throughout their home.

The first milestone to implement is:

DROP 1 - AUTHENTICATION FOUNDATION

The generated repository must be production-quality and compile successfully.

---

# TECHNOLOGY STACK

## Backend

- .NET 9
- ASP.NET Core Web API
- Entity Framework Core
- PostgreSQL
- Swagger / OpenAPI
- JWT Authentication

## Frontend (Future)

- Next.js
- TypeScript
- Tailwind CSS

## Mobile (Future)

- React Native
- Expo
- TypeScript

## Infrastructure

- Docker
- Docker Compose
- GitHub Actions

---

# SOLUTION STRUCTURE

Create exactly this solution structure:

PantryPortal.sln

src/

    PantryPortal.Api/

    PantryPortal.Application/

    PantryPortal.Domain/

    PantryPortal.Infrastructure/

    PantryPortal.Persistence/

    PantryPortal.Contracts/

tests/

    PantryPortal.Tests/

docker/

database/

docs/

.github/

---

# CLEAN ARCHITECTURE REQUIREMENTS

Dependency Direction:

Api
    -> Application

Application
    -> Domain

Infrastructure
    -> Application

Persistence
    -> Application

Domain
    -> No Dependencies

---

# DROP 1

# AUTHENTICATION FOUNDATION

Generate a COMPLETE runnable system.

The generated solution MUST:

- Compile successfully
- Run successfully
- Support Docker
- Support PostgreSQL
- Support Swagger
- Support JWT
- Include Unit Tests
- Include Integration Tests
- Include Migrations

---

# DOMAIN ENTITIES

## User

Generate:

```csharp
public class User
{
    public Guid Id { get; set; }

    public string Email { get; set; }

    public string PasswordHash { get; set; }

    public string FirstName { get; set; }

    public string LastName { get; set; }

    public bool IsEmailVerified { get; set; }

    public DateTime CreatedDate { get; set; }
}
```

## Role

Generate:

```csharp
public class Role
{
    public int Id { get; set; }

    public string Name { get; set; }
}
```

## UserRole

Generate:

```csharp
public class UserRole
{
    public Guid UserId { get; set; }

    public int RoleId { get; set; }

    public User User { get; set; }

    public Role Role { get; set; }
}
```

## RefreshToken

Generate:

```csharp
public class RefreshToken
{
    public Guid Id { get; set; }

    public Guid UserId { get; set; }

    public string Token { get; set; }

    public DateTime ExpirationDate { get; set; }

    public bool Revoked { get; set; }
}
```

---

# USER ROLE ENUM

Generate:

```csharp
public enum UserRoleType
{
    Owner = 1,
    Administrator = 2,
    Member = 3,
    Viewer = 4
}
```

---

# DATABASE

Database Provider:

PostgreSQL

Database Name:

pantryportal

---

# DATABASE TABLES

Generate Entity Framework entities, configurations, migrations and repository implementations for:

- Users
- Roles
- UserRoles
- RefreshTokens

---

# USERS TABLE

Create migration equivalent to:

```sql
CREATE TABLE Users
(
    Id UUID PRIMARY KEY,

    Email VARCHAR(255) NOT NULL UNIQUE,

    PasswordHash TEXT NOT NULL,

    FirstName VARCHAR(100),

    LastName VARCHAR(100),

    IsEmailVerified BOOLEAN NOT NULL,

    CreatedDate TIMESTAMP NOT NULL
);
```

---

# ROLES TABLE

```sql
CREATE TABLE Roles
(
    Id INTEGER PRIMARY KEY,

    Name VARCHAR(50) NOT NULL UNIQUE
);
```

Seed:

Owner

Administrator

Member

Viewer

---

# USERROLES TABLE

```sql
CREATE TABLE UserRoles
(
    UserId UUID NOT NULL,

    RoleId INTEGER NOT NULL,

    PRIMARY KEY(UserId, RoleId)
);
```

---

# REFRESHTOKENS TABLE

```sql
CREATE TABLE RefreshTokens
(
    Id UUID PRIMARY KEY,

    UserId UUID NOT NULL,

    Token TEXT NOT NULL,

    ExpirationDate TIMESTAMP NOT NULL,

    Revoked BOOLEAN NOT NULL
);
```

---

# ENTITY FRAMEWORK CORE

Generate:

ApplicationDbContext

Configurations

Repositories

Dependency Injection Registration

Migrations

Database Seeding

---

# AUTHENTICATION

Use:

JWT Bearer Authentication

Password Hashing:

BCrypt.Net

---

# JWT CONFIGURATION

Issuer:

PantryPortal

Audience:

PantryPortal

Access Token Lifetime:

12 Hours

Refresh Token Lifetime:

30 Days

---

# AUTH CONTRACTS

Generate DTOs in PantryPortal.Contracts

## RegisterRequest

```csharp
public record RegisterRequest(
    string Email,
    string Password,
    string FirstName,
    string LastName
);
```

## LoginRequest

```csharp
public record LoginRequest(
    string Email,
    string Password
);
```

## RefreshTokenRequest

```csharp
public record RefreshTokenRequest(
    string RefreshToken
);
```

## AuthResponse

```csharp
public record AuthResponse(
    string AccessToken,
    string RefreshToken,
    DateTime ExpiresAt
);
```

## CurrentUserResponse

```csharp
public record CurrentUserResponse(
    Guid Id,
    string Email,
    string FirstName,
    string LastName
);
```

---

# AUTH SERVICES

Generate:

## JwtTokenGenerator

Responsibilities:

- Create JWT tokens
- Create refresh tokens
- Validate tokens

## PasswordHashService

Responsibilities:

- Hash passwords
- Verify passwords

## AuthenticationService

Responsibilities:

- Register user
- Login user
- Refresh token
- Logout user
- Get current user

---

# API CONTROLLERS

Generate:

AuthController

---

# AUTH ENDPOINTS

## Register

POST

/api/auth/register

Request

```json
{
  "email":"john@email.com",
  "password":"Password123!",
  "firstName":"John",
  "lastName":"Doe"
}
```

Response

```json
{
  "accessToken":"jwt",
  "refreshToken":"refresh",
  "expiresAt":"2026-01-01T00:00:00Z"
}
```

---

## Login

POST

/api/auth/login

Request