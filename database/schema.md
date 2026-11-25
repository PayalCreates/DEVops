# Schema

```mermaid
erDiagram
    USERS ||--o{ TASKS : owns
    USERS {
        int id PK
        varchar email UK "lower-cased, unique index"
        varchar full_name
        varchar hashed_password "bcrypt, cost 12"
        varchar role "admin | manager | user (CHECK)"
        bool is_active
        timestamptz created_at
    }
    TASKS {
        int id PK
        varchar title "1-200 chars"
        text description "nullable, <=5000"
        varchar status "todo | in_progress | done (CHECK)"
        varchar priority "low | medium | high | critical (CHECK)"
        date due_date "indexed"
        int owner_id FK "ON DELETE CASCADE"
        timestamptz created_at
        timestamptz updated_at
        timestamptz completed_at "set when status=done"
    }
```

Indexes: `users.email` (unique), `tasks.owner_id`, `tasks.status`, `tasks.priority`, `tasks.due_date`.

Enums are stored as `VARCHAR + CHECK` (`native_enum=False`) so adding a value is a
simple, reversible migration instead of an `ALTER TYPE`.
