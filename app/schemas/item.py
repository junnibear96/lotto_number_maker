"""Marshmallow schemas for Item."""

from __future__ import annotations

from marshmallow import Schema, fields


class ItemSchema(Schema):
    """Serialize Item."""

    id = fields.Int(required=True)
    name = fields.Str(required=True)


class ItemCreateSchema(Schema):
    """Validate create Item payload."""

    name = fields.Str(required=True)
