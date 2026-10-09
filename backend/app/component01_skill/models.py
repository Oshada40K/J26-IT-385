"""Persistence uses component-local SQLite assessment snapshots.

The shared app.database has no ORM Base or configured database yet. Table
creation and parameterized queries live in repository.py. Snapshot JSON retains
skill items, evidence, identifiers and method versions per historical assessment.
Replace this adapter with reviewed team ORM models/migrations when available.
"""
